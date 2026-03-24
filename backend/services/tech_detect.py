"""Technology Detection — Mostly programmatic, AI only for summary."""

import asyncio
import re
from .scraper import fetch_page, parse_html
from .ai_client import ask_ai


# ── Signature patterns for common technologies ─────────────────

TECH_SIGNATURES = {
    # CMS / Platforms
    "WordPress": {"meta": ["generator", "wordpress"], "scripts": ["wp-content", "wp-includes", "wp-json"], "html_attrs": ["wp-block-", "wp-element"]},
    "Shopify": {"meta": ["generator", "shopify"], "scripts": ["cdn.shopify.com", "shopify.com/s/"], "links": ["cdn.shopify.com"]},
    "Wix": {"scripts": ["static.parastorage.com", "wix.com"], "meta": ["generator", "wix"]},
    "Squarespace": {"scripts": ["squarespace.com", "sqsp"], "meta": ["generator", "squarespace"]},
    "Drupal": {"meta": ["generator", "drupal"], "scripts": ["drupal.js", "drupal.settings"], "html_attrs": ["data-drupal"]},
    "Joomla": {"meta": ["generator", "joomla"], "scripts": ["/media/jui/", "/media/system/js/"]},
    "Ghost": {"meta": ["generator", "ghost"], "links": ["ghost/"]},
    "Webflow": {"meta": ["generator", "webflow"], "scripts": ["webflow.js"], "html_attrs": ["data-wf-"]},
    "Gatsby": {"scripts": ["gatsby-", "/page-data/"], "html_attrs": ["___gatsby"]},
    "Hugo": {"meta": ["generator", "hugo"]},

    # Frontend Frameworks (expanded patterns for bundled JS)
    "React": {
        "scripts": ["react.production.min", "react-dom", "react.development", "/react.", "reactjs"],
        "html_attrs": ["data-reactroot", "data-reactid", "__next", "_reactListening"],
        "inline_js": ["__REACT_DEVTOOLS_GLOBAL_HOOK__", "react-app", "__reactFiber", "createRoot", "ReactDOM"],
        "html_ids": ["root", "app", "__next"],
    },
    "Next.js": {
        "scripts": ["_next/static", "_next/data", "next/router"],
        "html_attrs": ["__next", "__NEXT_DATA__"],
        "inline_js": ["__NEXT_DATA__", "__next", "next/router", "_nextData"],
        "html_ids": ["__next"],
    },
    "Vue.js": {
        "scripts": ["vue.min.js", "vue.js", "vue.runtime", "vue.global", "vue.esm", "/vue@"],
        "html_attrs": ["data-v-", "v-cloak", "v-if", "v-for", "v-bind", "v-on"],
        "inline_js": ["__VUE__", "__vue__", "Vue.createApp", "createApp", "Vue.component"],
        "html_ids": ["app"],
    },
    "Nuxt.js": {
        "scripts": ["_nuxt/", "nuxt.js"],
        "html_attrs": ["__nuxt", "data-n-head"],
        "inline_js": ["__NUXT__", "$nuxt", "nuxt.config"],
        "html_ids": ["__nuxt"],
    },
    "Angular": {
        "scripts": ["angular.min.js", "zone.js", "polyfills", "runtime.", "angular/core"],
        "html_attrs": ["ng-version", "ng-app", "_ngcontent", "_nghost", "ng-star-inserted"],
        "inline_js": ["ng.probe", "getAllAngularRootElements", "platformBrowserDynamic"],
    },
    "Svelte": {
        "scripts": ["svelte", ".svelte"],
        "html_attrs": ["svelte-", "data-svelte"],
        "inline_js": ["__svelte"],
    },
    "SvelteKit": {
        "scripts": ["_app/immutable", "sveltekit"],
        "html_attrs": ["data-sveltekit"],
        "inline_js": ["__sveltekit"],
    },
    "Remix": {
        "scripts": ["remix", "__remixContext"],
        "inline_js": ["__remixContext", "__remixManifest"],
    },
    "Astro": {
        "scripts": ["astro/"],
        "html_attrs": ["astro-", "data-astro"],
        "inline_js": ["astro:"],
    },
    "Ember.js": {
        "scripts": ["ember.js", "ember.min", "ember-cli"],
        "html_attrs": ["ember-view", "data-ember"],
        "html_ids": ["ember-basic-dropdown"],
    },
    "Backbone.js": {"scripts": ["backbone.min.js", "backbone.js"]},
    "Alpine.js": {"scripts": ["alpine", "cdn.jsdelivr.net/npm/alpinejs"], "html_attrs": ["x-data", "x-bind", "x-on", "x-show", "x-if"]},
    "Stimulus": {"scripts": ["stimulus"], "html_attrs": ["data-controller", "data-action", "data-target"]},
    "htmx": {"scripts": ["htmx.org", "htmx.min"], "html_attrs": ["hx-get", "hx-post", "hx-trigger", "hx-swap"]},
    "Turbo": {"scripts": ["turbo.es", "@hotwired/turbo"], "html_attrs": ["data-turbo"]},
    "Preact": {"scripts": ["preact", "preact.min"], "inline_js": ["preact"]},
    "Lit": {"scripts": ["lit-html", "lit-element", "@lit/"], "html_attrs": ["lit-"]},

    # CSS Frameworks
    "Bootstrap": {"scripts": ["bootstrap.min.js", "bootstrap.bundle"], "links": ["bootstrap.min.css", "bootstrap.css", "cdn.jsdelivr.net/npm/bootstrap"]},
    "Tailwind CSS": {"links": ["tailwind"], "html_classes_count": {"threshold": 10, "patterns": ["flex", "items-center", "justify-", "bg-", "text-", "px-", "py-", "mt-", "mb-", "rounded-", "shadow-", "w-", "h-", "grid", "gap-", "space-", "border-", "font-", "leading-", "tracking-", "min-", "max-"]}},
    "Material UI": {"scripts": ["material-ui", "@mui"], "links": ["material"], "html_attrs": ["MuiButton", "MuiPaper", "Mui"]},
    "Chakra UI": {"scripts": ["chakra-ui", "@chakra"], "html_attrs": ["chakra-"]},
    "Ant Design": {"scripts": ["antd"], "links": ["antd"], "html_attrs": ["ant-"]},
    "Bulma": {"links": ["bulma.min.css", "bulma.css"]},
    "Foundation": {"scripts": ["foundation.min.js"], "links": ["foundation.min.css"]},
    "Semantic UI": {"links": ["semantic.min.css"], "scripts": ["semantic.min.js"]},

    # Backend Frameworks (detected via headers, cookies, HTML patterns)
    "Ruby on Rails": {
        "headers": ["x-powered-by:phusion passenger", "server:passenger"],
        "cookies": ["_session_id", "_rails_"],
        "inline_js": ["csrf-token", "csrf-param"],
        "html_attrs": ["data-turbo", "data-remote", "data-confirm"],
        "meta_names": ["csrf-token", "csrf-param"],
    },
    "Django": {
        "headers": ["x-powered-by:django"],
        "cookies": ["csrftoken", "sessionid", "django_language"],
        "inline_js": ["django", "csrfmiddlewaretoken"],
        "html_attrs": ["csrfmiddlewaretoken"],
    },
    "Laravel": {
        "headers": ["x-powered-by:laravel"],
        "cookies": ["laravel_session", "XSRF-TOKEN"],
        "inline_js": ["Laravel", "livewire"],
        "html_attrs": ["data-csrf"],
    },
    "Express.js": {
        "headers": ["x-powered-by:express"],
    },
    "ASP.NET": {
        "headers": ["x-powered-by:asp.net", "x-aspnet-version"],
        "cookies": ["asp.net_sessionid", ".aspnetcore."],
        "html_attrs": ["__VIEWSTATE", "__EVENTVALIDATION", "data-ajax"],
    },
    "Flask": {
        "headers": ["server:werkzeug"],
        "cookies": ["session"],
    },
    "FastAPI": {
        "headers": ["server:uvicorn"],
    },
    "Spring": {
        "headers": ["x-application-context"],
        "cookies": ["JSESSIONID"],
    },
    "Phoenix": {
        "html_attrs": ["phx-", "data-phx"],
        "inline_js": ["phoenix", "LiveSocket"],
    },

    # Programming Languages (from headers/responses)
    "PHP": {
        "headers": ["x-powered-by:php"],
        "cookies": ["PHPSESSID"],
    },
    "Java": {
        "cookies": ["JSESSIONID"],
    },
    "Python": {
        "headers": ["server:gunicorn", "server:uvicorn", "server:waitress", "server:daphne"],
    },
    "Node.js": {
        "headers": ["x-powered-by:express", "x-powered-by:next.js", "x-powered-by:nuxt"],
    },
    "Ruby": {
        "headers": ["x-powered-by:phusion passenger", "server:puma", "server:unicorn", "server:thin", "server:passenger"],
    },

    # JS Libraries
    "jQuery": {"scripts": ["jquery.min.js", "jquery-", "jquery.js", "code.jquery.com"]},
    "GSAP": {"scripts": ["gsap.min.js", "gsap", "greensock", "cdnjs.cloudflare.com/ajax/libs/gsap"]},
    "Three.js": {"scripts": ["three.min.js", "three.js", "three.module"]},
    "Lodash": {"scripts": ["lodash.min.js", "lodash.js", "lodash.core"]},
    "D3.js": {"scripts": ["d3.min.js", "d3.js", "d3.v", "cdn.jsdelivr.net/npm/d3"]},
    "Moment.js": {"scripts": ["moment.min.js", "moment.js"]},
    "Axios": {"scripts": ["axios.min.js", "cdn.jsdelivr.net/npm/axios"]},

    # State Management
    "Redux": {"scripts": ["redux.min.js", "redux"], "inline_js": ["__REDUX_DEVTOOLS_EXTENSION__", "createStore"]},
    "MobX": {"scripts": ["mobx"], "inline_js": ["mobx"]},

    # Build Tools (detectable from output)
    "Webpack": {"scripts": ["webpack", "webpackJsonp", "webpackChunk"], "inline_js": ["webpackJsonp", "webpackChunk", "__webpack_require__"]},
    "Vite": {"scripts": ["/@vite", "vite/"], "html_attrs": ["data-vite"]},
    "Parcel": {"scripts": ["parcel"]},

    # Analytics
    "Google Analytics": {"scripts": ["google-analytics.com/analytics", "googletagmanager.com", "gtag/js", "ga.js", "analytics.js"]},
    "Google Tag Manager": {"scripts": ["googletagmanager.com/gtm"]},
    "Facebook Pixel": {"scripts": ["connect.facebook.net/en_US/fbevents", "fbevents.js"]},
    "Hotjar": {"scripts": ["static.hotjar.com"]},
    "Mixpanel": {"scripts": ["cdn.mxpnl.com", "mixpanel"]},
    "Segment": {"scripts": ["cdn.segment.com"]},
    "Amplitude": {"scripts": ["cdn.amplitude.com", "amplitude"]},
    "Heap": {"scripts": ["heap-", "cdn.heapanalytics.com"]},
    "Plausible": {"scripts": ["plausible.io"]},
    "Matomo": {"scripts": ["matomo.js", "piwik.js"]},
    "Clarity": {"scripts": ["clarity.ms"]},

    # CDN / Performance
    "Cloudflare": {"headers": ["cf-ray", "cf-cache-status", "server:cloudflare"]},
    "Fastly": {"headers": ["x-served-by", "x-fastly", "via:varnish"]},
    "Akamai": {"headers": ["x-akamai"]},
    "AWS CloudFront": {"headers": ["x-amz-cf-", "via:cloudfront"], "scripts": ["cloudfront.net"]},
    "Vercel": {"headers": ["x-vercel-id", "server:vercel", "x-vercel-cache"]},
    "Netlify": {"headers": ["x-nf-request-id", "server:netlify"]},
    "Heroku": {"headers": ["via:vegur", "via:1.1 vegur"]},
    "GitHub Pages": {"headers": ["server:github.com"]},
    "Firebase": {"scripts": ["firebase", "firebaseapp.com"], "headers": ["x-firebase"]},

    # Others
    "Google Fonts": {"links": ["fonts.googleapis.com", "fonts.gstatic.com"]},
    "Font Awesome": {"links": ["font-awesome", "fontawesome", "use.fontawesome.com"], "scripts": ["fontawesome"]},
    "Stripe": {"scripts": ["js.stripe.com"]},
    "Intercom": {"scripts": ["widget.intercom.io"]},
    "Drift": {"scripts": ["js.driftt.com"]},
    "Crisp": {"scripts": ["client.crisp.chat"]},
    "HubSpot": {"scripts": ["js.hs-scripts.com", "hubspot"]},
    "Zendesk": {"scripts": ["static.zdassets.com"]},
    "reCAPTCHA": {"scripts": ["google.com/recaptcha"]},
    "hCaptcha": {"scripts": ["hcaptcha.com"]},
    "Sentry": {"scripts": ["browser.sentry-cdn.com", "sentry.io"]},
    "LaunchDarkly": {"scripts": ["launchdarkly"]},
    "Algolia": {"scripts": ["algoliasearch", "algolia"]},
    "Elasticsearch": {"scripts": ["elasticsearch"]},
    "Socket.IO": {"scripts": ["socket.io"]},
    "GraphQL": {"scripts": ["graphql"], "inline_js": ["__APOLLO_STATE__", "graphql", "ApolloClient"]},
    "PWA / Service Worker": {"links": ["manifest.json"], "html_attrs": ["manifest"]},
    "AMP": {"scripts": ["cdn.ampproject.org"], "html_attrs": ["amp", "⚡"]},
    "Turbolinks": {"scripts": ["turbolinks"], "html_attrs": ["data-turbolinks"]},
    "Livewire": {"scripts": ["livewire"], "html_attrs": ["wire:"]},
    "Stimulus": {"scripts": ["stimulus"], "html_attrs": ["data-controller"]},
}


def _detect_from_html(html: str, soup, response) -> dict[str, dict]:
    """Detect technologies from HTML content, headers, and parsed soup."""
    detected = {}
    html_lower = html.lower()
    all_scripts_src = " ".join(
        tag.get("src", "") for tag in soup.find_all("script")
    ).lower()
    all_inline_js = " ".join(
        (tag.string or "") for tag in soup.find_all("script") if not tag.get("src")
    ).lower()
    all_scripts = all_scripts_src + " " + all_inline_js
    all_links = " ".join(tag.get("href", "") for tag in soup.find_all("link")).lower()
    all_attrs = str(soup).lower()
    headers_lower = {k.lower(): v.lower() for k, v in response.headers.items()}
    all_headers_str = " ".join(f"{k}:{v}" for k, v in headers_lower.items())

    # Extract cookies from Set-Cookie headers
    all_cookies = " ".join(
        v for k, v in response.headers.items() if k.lower() == "set-cookie"
    ).lower() if "set-cookie" in headers_lower else ""

    # Extract all HTML element IDs
    all_ids = " ".join(tag.get("id", "") for tag in soup.find_all(True) if tag.get("id")).lower()

    # Extract all HTML class names
    all_classes = " ".join(
        " ".join(tag.get("class", [])) for tag in soup.find_all(True) if tag.get("class")
    ).lower()

    # Extract all meta tag names for backend detection
    all_meta_names = {
        tag.get("name", "").lower(): tag.get("content", "").lower()
        for tag in soup.find_all("meta") if tag.get("name")
    }

    for tech_name, sigs in TECH_SIGNATURES.items():
        confidence = "Low"
        matches = []

        # Check script src / inline
        for pattern in sigs.get("scripts", []):
            if pattern.lower() in all_scripts:
                matches.append(f"script: {pattern}")

        # Check link href
        for pattern in sigs.get("links", []):
            if pattern.lower() in all_links:
                matches.append(f"link: {pattern}")

        # Check meta tags (paired format: [name, value, name, value, ...])
        for i in range(0, len(sigs.get("meta", [])), 2):
            if i + 1 < len(sigs.get("meta", [])):
                attr_name = sigs["meta"][i]
                attr_val = sigs["meta"][i + 1]
                meta_tag = soup.find("meta", attrs={"name": attr_name})
                if meta_tag and attr_val in (meta_tag.get("content", "")).lower():
                    matches.append(f"meta[{attr_name}]")

        # Check HTML attributes / class names in raw HTML
        for attr in sigs.get("html_attrs", []):
            if attr.lower() in all_attrs:
                matches.append(f"attr: {attr}")

        # Check inline JavaScript globals / patterns
        for pattern in sigs.get("inline_js", []):
            if pattern.lower() in html_lower:
                matches.append(f"inline: {pattern}")

        # Check HTML element IDs
        for id_pattern in sigs.get("html_ids", []):
            if id_pattern.lower() in all_ids:
                matches.append(f"id: #{id_pattern}")

        # Check HTTP headers
        for hdr in sigs.get("headers", []):
            if ":" in hdr:
                key, val = hdr.split(":", 1)
                key, val = key.strip().lower(), val.strip().lower()
                if key in headers_lower and val in headers_lower[key]:
                    matches.append(f"header: {hdr}")
            elif hdr.lower() in all_headers_str:
                matches.append(f"header: {hdr}")

        # Check cookies
        for cookie in sigs.get("cookies", []):
            if cookie.lower() in all_cookies:
                matches.append(f"cookie: {cookie}")

        # Check meta names (for CSRF tokens etc.)
        for meta_name in sigs.get("meta_names", []):
            if meta_name.lower() in all_meta_names:
                matches.append(f"meta-name: {meta_name}")

        # Special: Tailwind CSS class count detection
        if "html_classes_count" in sigs:
            class_cfg = sigs["html_classes_count"]
            count = 0
            for pattern in class_cfg["patterns"]:
                if pattern in all_classes:
                    count += 1
            if count >= class_cfg["threshold"]:
                matches.append(f"css-classes: {count} Tailwind patterns matched")

        if matches:
            if len(matches) >= 3:
                confidence = "High"
            elif len(matches) >= 2:
                confidence = "Medium"
            detected[tech_name] = {"confidence": confidence, "evidence": matches}

    # ── Extra detections ────────────────────────────
    # SSL
    if response.url.startswith("https"):
        detected["HTTPS/SSL"] = {"confidence": "High", "evidence": ["URL uses HTTPS"]}

    # Detect server from header
    server = headers_lower.get("server", "")
    if server:
        detected[f"Server: {response.headers.get('server', server)}"] = {
            "confidence": "High",
            "evidence": [f"Server header: {server}"],
        }

    # Detect X-Powered-By
    powered = headers_lower.get("x-powered-by", "")
    if powered:
        detected[f"Powered-By: {response.headers.get('X-Powered-By', powered)}"] = {
            "confidence": "High",
            "evidence": [f"X-Powered-By: {powered}"],
        }

    # Detect Open Graph
    og_tags = soup.find_all("meta", property=re.compile(r"^og:"))
    if og_tags:
        detected["Open Graph"] = {
            "confidence": "High",
            "evidence": [f"{len(og_tags)} OG tags found"],
        }

    # Detect Twitter Cards
    twitter_tags = soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
    if not twitter_tags:
        twitter_tags = soup.find_all("meta", attrs={"property": re.compile(r"^twitter:")})
    if twitter_tags:
        detected["Twitter Cards"] = {
            "confidence": "High",
            "evidence": [f"{len(twitter_tags)} Twitter Card tags found"],
        }

    # Detect Schema.org / JSON-LD
    ld_scripts = soup.find_all("script", type="application/ld+json")
    if ld_scripts:
        detected["Schema.org / JSON-LD"] = {
            "confidence": "High",
            "evidence": [f"{len(ld_scripts)} structured data blocks"],
        }

    # Detect viewport meta (mobile-responsive)
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport:
        detected["Responsive Design"] = {
            "confidence": "High",
            "evidence": [f"viewport: {viewport.get('content', '')[:60]}"],
        }

    # Detect Canonical URL
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical:
        detected["Canonical URL"] = {
            "confidence": "High",
            "evidence": [f"canonical: {canonical.get('href', '')[:60]}"],
        }

    return detected


def _structure_results(detected: dict[str, dict], url: str) -> dict:
    """Structure detected technologies into categorized JSON."""

    categories_map = {
        "CMS / Platform": ["WordPress", "Shopify", "Wix", "Squarespace", "Drupal", "Joomla", "Ghost", "Webflow", "Gatsby", "Hugo"],
        "Frontend Framework": ["React", "Next.js", "Vue.js", "Nuxt.js", "Angular", "Svelte", "SvelteKit", "Remix", "Astro", "Ember.js", "Backbone.js", "Alpine.js", "Preact", "Lit", "htmx", "Turbo", "Stimulus"],
        "Backend Framework": ["Ruby on Rails", "Django", "Laravel", "Express.js", "ASP.NET", "Flask", "FastAPI", "Spring", "Phoenix"],
        "Programming Language": ["PHP", "Java", "Python", "Node.js", "Ruby"],
        "CSS Framework": ["Bootstrap", "Tailwind CSS", "Material UI", "Chakra UI", "Ant Design", "Bulma", "Foundation", "Semantic UI"],
        "JavaScript Library": ["jQuery", "GSAP", "Three.js", "Lodash", "D3.js", "Moment.js", "Axios"],
        "State Management": ["Redux", "MobX"],
        "Build Tool": ["Webpack", "Vite", "Parcel"],
        "Analytics & Tracking": ["Google Analytics", "Google Tag Manager", "Facebook Pixel", "Hotjar", "Mixpanel", "Segment", "Amplitude", "Heap", "Plausible", "Matomo", "Clarity"],
        "Hosting & CDN": ["Cloudflare", "Fastly", "Akamai", "AWS CloudFront", "Vercel", "Netlify", "Heroku", "GitHub Pages", "Firebase"],
        "UI & Design": ["Google Fonts", "Font Awesome"],
        "Third-Party Services": ["Stripe", "Intercom", "Drift", "Crisp", "HubSpot", "Zendesk", "reCAPTCHA", "hCaptcha", "Sentry", "LaunchDarkly", "Algolia", "Elasticsearch", "Socket.IO", "GraphQL"],
        "SEO & Metadata": ["Open Graph", "Twitter Cards", "Schema.org / JSON-LD", "Canonical URL", "Responsive Design"],
        "Security": ["HTTPS/SSL"],
        "Progressive Web": ["PWA / Service Worker", "AMP", "Turbolinks", "Livewire"],
    }

    categories = {}
    categorized_keys = set()

    for cat_name, tech_names in categories_map.items():
        found = []
        for t in tech_names:
            if t in detected:
                found.append({"name": t, "confidence": detected[t]["confidence"], "evidence": detected[t]["evidence"]})
                categorized_keys.add(t)
        if found:
            categories[cat_name] = found

    # Server & Infrastructure: capture Server:/Powered-By: entries
    infra = []
    for key in detected:
        if key.startswith("Server:") or key.startswith("Powered-By:"):
            infra.append({"name": key, "confidence": detected[key]["confidence"], "evidence": detected[key]["evidence"]})
            categorized_keys.add(key)
    if infra:
        categories["Server & Infrastructure"] = infra

    # Catch any uncategorized techs
    uncategorized = []
    for key in detected:
        if key not in categorized_keys:
            uncategorized.append({"name": key, "confidence": detected[key]["confidence"], "evidence": detected[key]["evidence"]})
    if uncategorized:
        if "Other" not in categories:
            categories["Other"] = []
        categories["Other"].extend(uncategorized)

    # Confidence summary
    conf = {"High": 0, "Medium": 0, "Low": 0}
    for info in detected.values():
        conf[info["confidence"]] = conf.get(info["confidence"], 0) + 1

    return {
        "url": url,
        "total_detected": len(detected),
        "categories": categories,
        "confidence_summary": conf,
    }


async def detect(url: str) -> dict:
    """Main entry point: scrape the page then optionally ask AI for a summary."""
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return {"error": f"Could not fetch {url}. Check the URL and try again."}

    soup = parse_html(resp.text)
    detected = _detect_from_html(resp.text, soup, resp)
    result = _structure_results(detected, url)

    # Only call AI if we want a polished summary on top of raw detection
    if len(detected) >= 3:
        # Build a concise text version for the AI prompt
        report_lines = []
        for cat, techs in result["categories"].items():
            report_lines.append(f"### {cat}")
            for t in techs:
                report_lines.append(f"  • {t['name']} [{t['confidence']}] — {', '.join(t['evidence'])}")
        report_text = "\n".join(report_lines)

        try:
            summary = await ask_ai(
                "You are a web technology analyst. Given a raw technology detection report, "
                "add brief SEO impact notes for each detected technology and provide 3-5 "
                "actionable recommendations. Keep it concise.",
                f"Here is the detection report:\n\n{report_text}\n\nAdd SEO impact notes and recommendations.",
                1500,
            )
            result["ai_summary"] = summary
        except Exception:
            pass  # If AI fails, return without summary

    return result

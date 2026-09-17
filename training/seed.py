"""Authored bootstrap examples, NOT observations of real websites.

Split scenario families before augmenting. Variants never cross a split.
Do not interpret this small, English-only corpus as web-wide validation.
"""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "ad": """
Advertisement|advertisement banner|ads.vendor.test/display/banner
Sponsored · Discover the new electric car|sponsored card|offers.vendor.test/click
Promoted · Try our cloud hosting today|promoted placement|cloud.vendor.test/landing
Ad · Save on your next flight|ad unit|travel.vendor.test/creative
Advertising|display-ad-container|ads.vendor.test/render
Paid partnership · Explore summer travel|partner advertisement|travel.vendor.test/promotion
Sponsored content · A smarter way to invest|native sponsored|finance.vendor.test/offer
Advertisement · Shop the latest collection|advertisement slot|shop.vendor.test/banner
Promoted by Example · Start your free trial|promoted-story|service.vendor.test/signup
Ad choices · Learn more|adchoices creative|ad.vendor.test/delivery
|google_ads_iframe banner|securepubads.g.doubleclick.net/gampad/ads
|adsbygoogle ad-slot|pagead2.googlesyndication.com/pagead
|gpt-ad leaderboard|adserver.vendor.test/banner
|dfp-ad rectangle|ads.vendor.test/serve
Sponsored links · Recommended for you|outbrain sponsored|widgets.outbrain.com/content
From our advertising partners|taboola-ad sponsored|cdn.taboola.com/libtrc
Paid advertisement · Compare insurance rates|paid-placement|insure.vendor.test/campaign
This space is reserved for advertising|advert-slot-placeholder|
Support our sponsor · Fast secure hosting|sponsor-banner|hosting.vendor.test/offer
Publicité · Découvrez notre offre|advertising banner|pub.vendor.test/ads
Anzeige · Jetzt entdecken|ad-wrapper|werbung.vendor.test/banner
Advertise here|ad-placement banner|publisher.test/advertise
Sponsored · Download this productivity app|sponsor-card|app.vendor.test/install
Paid promotion · Limited time offer|native-ad-promotion|deals.vendor.test/buy
""",
    "cookie": """
We use cookies to improve your experience. Accept all Reject all Manage preferences|cookie-consent-banner|
Your privacy matters. We and our partners use cookies. Agree and continue|privacy-consent|
This website uses cookies. Accept cookies Cookie settings|cookie-notice|
Allow cookies? Necessary only Accept all|consent-dialog|
We value your privacy. Store and access information on a device. Manage options|cmp-container|
Cookies help us personalize content and ads. Reject optional cookies|cookie-policy-modal|
Before you continue, choose your cookie preferences|consent-overlay|
Our partners process personal data. I agree Manage consent|cmp-dialog|
Privacy preferences. Functional Analytics Marketing Save choices|cookie-settings-panel|
Accept tracking cookies to personalize your visit. Decline|tracking-consent|
We respect your privacy. Accept all cookies Reject all cookies|onetrust-banner-sdk|
We use essential and optional cookies. Customize choices|cookiebot-dialog|
Consent to data processing. Vendors and purposes. Confirm selections|privacy-cmp|
This site uses cookies and similar technologies. Allow all|consent-banner|
Choose how we use your data. Accept Reject Preferences|privacy-popup|
Cookie settings. Strictly necessary cookies are always active|cookies-modal|
Nous utilisons des cookies. Tout accepter Tout refuser|cookie-consent|
Wir verwenden Cookies. Alle akzeptieren Ablehnen|cookie-banner|
Your privacy choices. Do not sell or share my personal information|consent-prompt|
Allow us to measure visits with cookies? Yes No|cookie-permission|
""",
    "newsletter": """
Get our newsletter. Enter your email to subscribe. No thanks|newsletter-modal|
Join our mailing list for weekly updates. Sign up Dismiss|signup-popup|
Stay in the loop. Subscribe to our free newsletter|newsletter-overlay|
Don't miss a story. Get the daily briefing in your inbox|email-capture|
Subscribe for weekly recipes delivered to your inbox|newsletter-signup-popup|
Want more like this? Join our email list. Maybe later|mailing-list-prompt|
Get 10 percent off your first order. Enter email Join|email-discount-modal|
Sign up for our weekly digest. Email address Subscribe|digest-popup|
Before you go, join our free newsletter|exit-intent-newsletter|
Be the first to know. Get updates by email|email-signup-overlay|
Enjoyed reading? Subscribe to the morning newsletter|newsletter-lightbox|
Free tips in your inbox. Enter your email Get updates|subscription-prompt|
Join thousands of readers. Email address Sign me up|newsletter-promotion|
Subscribe to the newsletter. No spam, unsubscribe anytime|newsletter-dialog|
Your weekly dose of science. Send me the newsletter|email-newsletter-modal|
Receive breaking stories by email. Join the mailing list|mailing-list-dialog|
Get exclusive email offers. Sign up now|email-offer-popup|
Let's keep in touch. Subscribe by email|signup-lightbox|
Inscrivez-vous à notre newsletter. Votre adresse email|newsletter-popup|
Newsletter abonnieren. E-Mail eingeben|newsletter-overlay|
""",
    "notification": """
Enable push notifications to stay up to date. Allow Not now|push-permission-prompt|
Get breaking news alerts. Turn on notifications|notification-permission|
Would you like to receive notifications? Yes Later|push-subscribe|
Allow this site to send you notifications|notifications-modal|
Never miss an update. Enable browser notifications|web-push-prompt|
Stay informed with push alerts. Subscribe No thanks|push-notification|
Turn on notifications for the latest deals|push-optin|
We'd like to send you news alerts. Allow Block|notification-dialog|
Click allow to receive desktop notifications|onesignal-popover|
Get notified when new stories are published. Enable alerts|browser-notification-prompt|
Receive sports results with push notifications|push-permission|
Enable notifications for live coverage. Not now|notification-optin|
Don't miss important updates. Allow notifications|push-message|
Stay connected. Subscribe to browser alerts|push-popup|
Allow notifications from this website? Later Allow|notification-request|
Instant alerts straight to your browser. Enable|push-subscription-modal|
Would you like breaking news notifications?|webpush-dialog|
Get price alerts. Enable push notifications|push-offer|
Activer les notifications? Autoriser Plus tard|notification-popup|
Benachrichtigungen aktivieren. Später Zulassen|push-notification|
""",
    "paywall": """
Subscribe to continue reading. Already a subscriber? Sign in|paywall-overlay|
You've reached your free article limit. Unlock unlimited access|metered-paywall|
This article is for subscribers only. Subscribe now|subscription-wall|
Become a member to read the full story|premium-content-gate|
To keep reading, start your subscription|paywall-modal|
Unlock this article with a digital subscription|article-paywall|
Your free trial has ended. Subscribe to read more|subscription-gate|
Premium article. Sign in or purchase access|premium-wall|
You have read all your free articles this month|meter-message paywall|
Support independent journalism. Subscribe to unlock the full article|reader-revenue-wall|
This content is available exclusively to paid members|membership-gate|
Continue reading with a paid subscription. View plans|paid-content-overlay|
Want the full story? Subscribe for unlimited reading|subscription-paywall|
Subscribers get access to this investigation. Join today|premium-overlay|
You need a subscription to access the rest of this article|content-paywall|
Read without limits. Subscribe to unlock this story|metered-access-modal|
Already a member? Log in to read this premium article|membership-paywall|
Purchase this article or start a monthly subscription|article-purchase-wall|
Abonnez-vous pour lire la suite de cet article|paywall-abonnement|
Jetzt abonnieren und weiterlesen|abo-paywall|
""",
    "content": """
How online advertising works: a guide to ad auctions|article-summary|news.publisher.test/ads-explained
The history of cookies and web privacy|story-card|news.publisher.test/privacy
Manage your notification settings|account-settings|app.publisher.test/settings
Newsletter archive: read past editions|newsletter-archive|publisher.test/archive
Subscription plans and pricing|pricing-table|publisher.test/plans
Chocolate chip cookie recipe|recipe-card|food.publisher.test/cookies
Ad blockers compared in our independent review|review-card|tech.publisher.test/reviews
Today's latest headlines|news-grid|publisher.test/news
Sign in to your account. Email Password|login-dialog|publisher.test/login
Your shopping cart. Review order and checkout|cart-dialog|shop.publisher.test/cart
Confirm payment. Card number Expiry Security code|checkout-modal|shop.publisher.test/pay
Are you sure you want to delete this project? Cancel Delete|confirmation-dialog|
Choose a file to upload. Cancel Upload|upload-modal|
Search results for sponsored research|search-results|
This research was sponsored by the university|research-abstract|
Advertisement is the title of a poem published in 1922|library-entry|
We build advertising software for small businesses|product-description|company.publisher.test/product
Learn how to create an ad campaign|tutorial-card|docs.publisher.test/advertising
Banner component documentation and code examples|component-demo|docs.publisher.test/banner
Your subscription is active. Next renewal October 1|account-billing|
Buy winter boots. Size Color Add to cart|product-card|shop.publisher.test/products
Weather forecast: clear skies tomorrow|weather-widget|
Contact support. Tell us what went wrong|support-dialog|
Video transcript and playback controls|video-player|
Recommended articles from our editors|related-stories|
Accept or decline this meeting invitation|calendar-dialog|
Enable notifications in the Settings app: troubleshooting guide|help-card|
Cookie consent laws explained by a privacy researcher|article-card|
Newsletter design templates for email marketers|template-gallery|
How newspapers use paywalls to fund journalism|article-teaser|
Save your changes? Cancel Discard Save|unsaved-dialog|
Sponsored research disclosure and author affiliations|paper-metadata|
Choose your language. English Français Deutsch|language-picker|
Accessibility preferences. Contrast Text size|accessibility-panel|
Special offers in our store. Browse all products|shop-collection|
Log in to manage your newsletter subscriptions|account-newsletters|
Your browser blocked a popup. Learn how to change settings|help-article|
Enable two-factor authentication. Enter verification code|security-dialog|
Product added to your cart. Continue shopping|cart-confirmation|
Terms and conditions. I agree Cancel|terms-dialog|
Order confirmed. Thank you for shopping with us|order-status|
This course teaches display advertising and marketing|course-card|
Accept cookies button implementation in JavaScript|code-example|
Read more about our subscriber benefits|membership-card|
Go to next page. Previous Next|pagination|
Live scores and match results|scoreboard|
Suggested contacts. Connect Message|people-card|
New message from your teammate. Reply|chat-panel|
No results found. Try another search|empty-state|
Manage consent records for your organization|admin-panel|
""",
}


def main():
    rows = []
    for label, block in SCENARIOS.items():
        scenarios = [line.strip().split('|') for line in block.strip().splitlines()]
        order = list(range(len(scenarios)))
        random.Random(817).shuffle(order)
        splits = {i: ('train' if rank < len(order)*0.6 else 'validation' if rank < len(order)*0.8 else 'test') for rank, i in enumerate(order)}
        for i, (text, attrs, resource) in enumerate(scenarios):
            family = f'{label}-{i:03d}'
            rng = random.Random(family)
            for variant in range(8):
                overlay = label in {'cookie', 'newsletter', 'notification', 'paywall'} or (label == 'content' and ('dialog' in attrs or 'modal' in attrs))
                width, height = rng.choice([(300, 250), (728, 90), (320, 100), (600, 340), (970, 250)])
                fixed = overlay or (label == 'ad' and variant == 4)
                state = {
                    'text': text if variant != 7 or label != 'ad' else '',
                    'attributes': (attrs if variant < 5 else f'widget-{i*13+variant}') + (f' component-{variant}' if variant % 2 else ''),
                    'resource': resource if variant % 3 else '',
                    'tag': rng.choice(['div', 'section', 'aside']),
                    'role': 'dialog' if overlay and variant % 2 else '',
                    'fixed': fixed, 'dialog': overlay and variant % 2 == 1,
                    'iframe': label == 'ad' and (not text or variant % 4 == 0),
                    'image': variant % 2 == 0,
                    'thirdParty': bool(resource) and variant % 3 != 0,
                    'width': width, 'height': height, 'links': rng.randint(0, 4),
                    'hasForm': overlay and variant % 3 != 0,
                    'protected': label == 'content' and any(word in attrs for word in ['login', 'checkout', 'security']),
                    'bannerShape': height <= 120 or width == 300,
                    'visible': True,
                }
                # Content can legitimately share ad-style dimensions and third-party links.
                rows.append({'id': f'{family}-{variant}', 'group': family, 'split': splits[i], 'label': label,
                             'source': 'authored-bootstrap-v1', 'state': state})
    path = ROOT / 'data/bootstrap.jsonl'
    path.write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows))
    print(json.dumps({'rows': len(rows), 'families': sum(len(b.strip().splitlines()) for b in SCENARIOS.values()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()

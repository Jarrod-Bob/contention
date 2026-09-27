# YouTube API Services terms and Developer Policies: a compliance checklist for contention

Follows up [the YouTube Data API research note](https://github.com/Jarrod-Bob/contention/blob/research/youtube-data-api/docs/research/youtube-data-api.md), section 5 "Storage and derived-metric policies", and tests the policy line in [ADR 0003](../adr/0003-predict-raw-log-views.md).

**This is not legal advice.** It is a careful reading of the published documents by a non-lawyer, written for a personal learning project whose owner doesn't want to put their Google account at risk. Where the text is ambiguous, this note says so instead of guessing.

All sources were read on **2026-09-27**. "Last updated" dates are as shown on each page:

| Document | Last updated shown |
|---|---|
| [YouTube API Services Terms of Service](https://developers.google.com/youtube/terms/api-services-terms-of-service) ("ToS") | 2026-09-14 |
| [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies) ("Policies") | 2026-09-14 |
| [Complying with YouTube's Developer Policies](https://developers.google.com/youtube/terms/developer-policies-guide) (the "Guide") | 2026-09-14 |
| [Additional policies for derived metrics and data storage](https://developers.google.com/youtube/terms/derived-metrics-policy) (the "Derived-metrics amendment") | 2026-09-14 |
| [Required Minimum Functionality](https://developers.google.com/youtube/terms/required-minimum-functionality) ("RMF") | 2026-09-14 |
| [Branding Guidelines](https://developers.google.com/youtube/terms/branding-guidelines) | 2025-08-20 |
| [Quota and Compliance Audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits) | 2026-09-14 |
| [Terms of Service revision history](https://developers.google.com/youtube/terms/revision-history) | latest entry: June 1, 2026 |
| [Google APIs Terms of Service](https://developers.google.com/terms) | "Last modified: November 9, 2021" |
| [Google Terms of Service](https://policies.google.com/terms) | "Effective July 30, 2026" |

The 2026-09-14 date on the developers.google.com pages looks like a site-wide stamp. The revision history lists no policy change after June 1, 2026. The ToS also has regional versions (Americas, APAC, EMEA, Russia). The [APAC version](https://developers.google.com/youtube/terms/api-services-terms-of-service-apac) matched the default one text for text when diffed.

## TL;DR

1. **Ids get no exemption.** The Policies have no carve-out for video or channel ids. Every piece of Non-Authorized Data, ids included, must be deleted or refreshed within 30 calendar days. Nothing fetched with the API key may be kept longer than that, and that includes derived data. The only exceptions are for Authorized Data (below) and for developers approved under the June 2026 Derived-metrics amendment. Even that amendment keeps "video titles, creator names, descriptions" on the 30-day rule. (High confidence.)
2. **Authorized Data can be kept longer, but only the statistics.** Stored Authorized Data is tied to "an active user" and must be re-checked every 30 days. The longer term covers YouTube Analytics and Reporting API data and statistics such as view counts. It lasts only "for as long as is necessary" for the user's consent, and every 30 days you must check that you're still authorized and that the Video still exists. Other Authorized Data, such as titles, still has a 30-day limit. (High confidence.)
3. **Rules for API clients with users have no single-user exemption.** The ToS and Policies define an "API Client" as any "software application … developed by you that accesses, or uses, the YouTube API Services". None of the privacy-policy, YouTube-ToS-link or branding requirements makes an exception for personal or internal tools. Read literally, they apply to contention. Some rules clearly don't apply because they're about uploads, embeds, comments, OAuth or children. Audits and quota forms are needed only to go above the default quota, or when YouTube asks. (Applicability: medium-high confidence. How strictly YouTube would enforce against a local tool: unknown.)
4. **The derived-data prohibition is broader than ADR 0003 assumes.** The Policies say API Clients must not "access or use API Data to create new or derived data or metrics". That prohibits *creating* derived data, not only presenting it. The Guide's list of "Don't use YouTube's API to" items names several of contention's core features almost word for word:
   - "Infer or estimate the content category/type of a video or channel" matches Format labels, and perhaps Themes.
   - "Estimate audience affinities, demographics, or audience composition" matches Audience labels and Audience groups.
   - "Calculate and assign custom 'scores' to channels based on … average view count" is close to the prior-uploads baseline and "the Channel's typical Video".

   The Derived-metrics amendment (May and June 2026) permits "Content Categorization and Tagging" and "Custom Channel Scores" **only** for audited analytics developers whose use case is accepted. That implies these are prohibited without that approval. Embeddings, clustering and view predictions aren't mentioned anywhere, so their status is genuinely unclear. (High confidence that the text reaches the labels. Unclear for embeddings and predictions.)
5. **Enforcement can reach the whole Google account.** The ToS allows suspending or terminating access, "including any credentials", and ending the Agreement. The Guide adds: "reduction of your API quota, revoking your API keys … or other actions, **including termination of the Google account associated with the API service**". The Google Terms of Service allow Google to "suspend or terminate your access to the services or delete your Google Account" for material breach of "service-specific additional terms, or policies". If the account is suspended, you may not access the API by any other means. (High confidence that the account is within reach. Likelihood for a low-volume personal tool: unknown.)

**Biggest gaps against the current design:**
- LLM-inferred Format and Audience labels.
- Clusters used as categories.
- The "did better or worse than expected" and "typical Video" comparisons.
- API Data sent to third-party LLMs (OpenRouter free models).
- No privacy policy, YouTube ToS link or YouTube attribution in the Streamlit UI.
- Persisted model artefacts that aren't covered by the 28-day purge.

The cleanest way to resolve the derived-data question is the route the Guide itself offers: "If … you're unsure whether your service is allowed, please apply for an API Compliance Audit". Otherwise, redesign the affected features. See [section 7](#7-compliance-checklist).

## 1. What the Agreement is, and what counts as API Data

The ToS says the Agreement is made up of: "these Terms of Service; the Developer Policies; the YouTube Guidelines [including the Branding Guidelines]; the credentials assigned to you …; the Google Software Principles …; and the YouTube Terms." If they contradict each other, the ToS takes precedence. ([ToS §2](https://developers.google.com/youtube/terms/api-services-terms-of-service#agreement))

Key definitions:

- **API Client:** "a website or software application (including a mobile application) developed by you that accesses, or uses, the YouTube API Services." ([ToS §1](https://developers.google.com/youtube/terms/api-services-terms-of-service#definitions); the same wording is in [Policies IV](https://developers.google.com/youtube/terms/developer-policies#definition-api-client))
- **API Data:** "data, content (including audiovisual content) and information provided to API Clients … through the YouTube API services". ([ToS preamble](https://developers.google.com/youtube/terms/api-services-terms-of-service#youtube-api-services-terms-of-service))
- **Non-Authorized Data:** "API Data accessible by an API Client without User Credentials." **Authorized Data:** "API Data that an active user expressly authorizes an API Client to access or otherwise use via User Credentials." ([Policies IV](https://developers.google.com/youtube/terms/developer-policies#definition-non-authorized-data))
- **Ownership:** YouTube keeps all rights in "all YouTube API Services (including all API Data) … and all derivative works of any of the foregoing". ([ToS §16.1](https://developers.google.com/youtube/terms/api-services-terms-of-service#no-implied-rights))

**The Guide's status:** "provides guidance and examples … The guide offers insight into how YouTube enforces certain aspects of the API TOS, but it does not replace any existing documents." ([Policies, note at top](https://developers.google.com/youtube/terms/developer-policies)) It isn't a binding document on its own, but it is YouTube's published reading of the binding ones.

**The Google APIs Terms of Service** apply "By accessing or using our APIs", and "If there is a conflict between these terms and additional terms applicable to a given API, the additional terms will control". ([Google APIs ToS, preamble](https://developers.google.com/terms)) *Interpretation (medium confidence):* the YouTube ToS doesn't list the Google APIs ToS as part of its Agreement. Even so, the Google APIs ToS very likely applies too, because the Data API is a Google API used through a Google Cloud project, and the YouTube-specific terms win wherever the two conflict.

*Interpretation:* contention is an API Client. Everything it gets from `channels.list`, `playlistItems.list` and `videos.list` with an API key is **Non-Authorized API Data**, including ids, titles, descriptions, tags and statistics.

## 2. Storage of public (Non-Authorized) data, and whether ids are exempt (Q1)

### What the text says

The storage rules are in [Policies III.E.4, "Refreshing, Storing, and Displaying API Data"](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content). Sub-letters follow the page's own cross-references ("III.E.4.b", anchors `III-E-4-i` and `III-E-4-j`).

- **III.E.4.d:** "API Clients may temporarily store limited amounts of Non-Authorized Data for as long as is necessary for the purposes of the API Client but not longer than 30 calendar days. As in section (III.E.4.c) immediately above, this means that after 30 calendar days, the API Client must either delete or refresh the stored data."
- **III.E.4.b, closing paragraph:** "To be clear, an API Client must not store statistics retrieved as Non-Authorized Data for more than 30 days. For example, an API Client must not store the subscriber count for a YouTube channel for more than 30 days without authorization from the channel owner."
- **III.E.4.e:** "In all cases, API Clients must use reasonable efforts to ensure that their stored API Data is consistent with the current data available through YouTube API Services. For example, API Clients should reflect metadata changes and viewcount updates as quickly as possible."
- **III.E.4.f:** "API Clients must display the most updated API Data available in their user-facing presentations … although API Clients may display historical API Data provided that it is presented accurately in context of time."
- **III.E, intro:** "Aside from the permissions and rights granted in this section, you and your API Clients have no further permissions or rights to API Data, including to temporarily stored API Data."

**No ids exemption.** None of the policy documents read for this note mention ids at all (search of the ToS, Policies, Guide and Derived-metrics amendment for "id", "ids" and "identifier"). The only storage exceptions are:

1. Authorization tokens (III.E.4.a).
2. Authorized Data statistics and Analytics/Reporting data (III.E.4.b; see section 3).
3. Approved developers under the Derived-metrics amendment. For them, the amendment says: "Policy III E.4.b, E.4.c, and E.4.d are amended to allow accepted API Clients to store metrics (e.g., views, likes, subs count, comment counts) from statistical endpoints for up to 36 calendar months. Derived metrics (such as sentiment analysis) based on retrieved data may also be stored for up to 36 calendar months. Other data (such as video titles, creator names, descriptions, and comment text) must still follow the 30-day refresh and deletion policy". ([Derived-metrics amendment, Data Storage](https://developers.google.com/youtube/terms/derived-metrics-policy#data-storage))

### Interpretation

**Q1 answer (high confidence): ids are not exempt.** A video id or channel id returned by the API is "information provided to API Clients through the YouTube API services", so it is API Data. Nothing in the text treats it differently. Keeping an id past 30 days without refreshing it (re-fetching the record and confirming it still exists) is outside what III.E.4.d permits. This matches the conclusion already written into ADR 0001 ("no exception lets API ids outlive the 30-day limit").

**May be kept beyond 30 days (non-approved developer, API key only):**
- Nothing that came from the API, unless it has been refreshed within the last 30 days. "Refresh" isn't defined. *Interpretation:* re-fetching the record through the API, and deleting it if the fetch shows it's gone, counts. III.E.4.b's example ("must also verify, every 30 days, that the video has not been deleted") supports this.
- Things that never came from the API: what the user wrote (Drafts, the niche description, the Format list, test queries). Also Channel **handles typed by the user**. *Interpretation (medium confidence):* a handle the user typed from their own knowledge isn't "provided … through the YouTube API services". The same handle, if it had been copied out of an API response, would be API Data. Tiers are typed by the user too, but they encode a subscriber band. *Interpretation (low risk, unclear):* acceptable while the user picks them by hand and the code never writes a Tier computed from an API `subscriberCount`.
- Aggregate eval scores such as nDCG or agreement rates, with no ids, titles or YouTube metrics in them. *Interpretation (medium confidence):* these measure contention's own system, not YouTube content. They are a small, unclear grey area under the literal "derived data" rule (section 4).

**May not be kept beyond 30 days:** ids, titles, descriptions, tags, topic categories, durations, publish dates, every statistic, Snapshots, and (under ADR 0003's line) everything derived from them. That includes anything *persisted* outside Postgres: trained LightGBM/CQR model files, cluster centroids, BM25 indexes, pickled numpy matrices, Streamlit caches, logs, LangChain/LangSmith traces and database backups.

**An open point: "limited amounts".** III.E.4.d allows storing "limited amounts" of Non-Authorized Data. The phrase isn't defined, and the planned Corpus is ~15–30k Videos and ~100–200 Channels. *Interpretation:* unclear whether that counts as "limited". No numeric threshold appears anywhere.

## 3. Authorized Data (Analytics and Reporting APIs) (Q2)

### What the text says

- **III.E.4.b:** "API Clients may store the following types of Authorized Data for as long as is necessary provided that the data is used for purposes consistent with the specific consent granted by an active user according to the applicable laws: data retrieved through the YouTube Analytics API service, data provided through the YouTube Reporting API service, or statistics provided through other YouTube API services, such as the number of views for a video … Note that even though an API Client may store this data for more than 30 days, the Client must still ensure every 30 days that it is still authorized by the user to access that data. For example, an API Client may store view counts for a video for more than 30 days, but it must still verify every 30 days that its authorization to access the video uploader's data has not been revoked. The API Client must also verify, every 30 days, that the video has not been deleted." ([Policies III.E](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content))
- **III.E.4.c:** "API Clients may store all other types of Authorized Data not identified in section (III.E.4.b) for as long as is necessary for the purposes of the specific consent granted by an active user and for no longer than 30 calendar days."
- **Revocation (III.D):** users need "a clearly explained and easy way … to revoke any authorization consent", and the client "must programmatically revoke that token right away". After that, "you and your API Clients must delete all Authorized Data that was accessed or stored pursuant to that consent … within 7 calendar days of the revocation". If consent is revoked through Google's security settings page instead, deletion "must take place within 30 calendar days", and "your API Clients will need to periodically reconfirm that its authorization tokens are still valid". ([Policies III.D](https://developers.google.com/youtube/terms/developer-policies#d.-accessing-youtube-api-services))
- **Privacy policy extras for Authorized Data (III.A.2.h–i):** the policy must say that users can revoke access at `https://security.google.com/settings/security/permissions`, and how to contact the developer. ([Policies III.A](https://developers.google.com/youtube/terms/developer-policies#a.-api-client-terms-of-use-and-privacy-policies))
- **Display restriction:** "API Clients must not display or allow access to Authorized Data to anyone other than the authorizing user or agents expressly approved by that user." ([Policies III.E.3](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content))
- **Scope minimisation:** "only request access to authorization scopes that they currently use … Do not try to future-proof your access". ([Policies III.D](https://developers.google.com/youtube/terms/developer-policies#d.-accessing-youtube-api-services))
- The Analytics and Reporting APIs "require authorization for all actions". (Policies III.D)

### Interpretation

**Q2 answer (high confidence): yes, but only the statistical and Analytics/Reporting data, and only on these terms:**
1. The data covers the channel whose owner granted OAuth consent. For contention that would be the user's own channel only.
2. It's kept only "as long as is necessary" for purposes within that consent. There's no fixed cap, but no "forever" either.
3. At least every 30 days, check that the token still refreshes and that each Video still exists. If either check fails, delete.
4. Delete within 7 days of an in-app revocation, and within 30 days of a revocation made through Google's settings.
5. Non-statistical Authorized Data, such as titles and descriptions fetched with OAuth, is still limited to 30 days (III.E.4.c).

Private creator analytics are **out of MVP scope** in the spec, so none of this applies today. If it's ever added, it would bring the Authorized-Data privacy-policy clauses, a revocation mechanism and a scoped consent screen with it.

## 4. Requirements aimed at API clients with users (Q3)

### Scoping language

The operative requirements are written about "API Clients" and "users", and none of them has a carve-out for single-user, personal or unpublished clients:

- **Privacy policy:** "Each API Client will provide and adhere to a published privacy policy that clearly and accurately describes to its users what user information you and your API Client access, collect and store". ([ToS §7](https://developers.google.com/youtube/terms/api-services-terms-of-service#user-privacy)) Also: "Each API Client must require users to agree to a privacy policy before users can access the API Client's features and functionality. The privacy policy must: be prominently displayed …, notify users that the API Client uses YouTube API Services, reference and link to the Google Privacy Policy at http://www.google.com/policies/privacy, clearly and comprehensively explain to users what user information, including API Data relating to users, the API Client accesses, collects, stores and otherwise uses …" ([Policies III.A.2](https://developers.google.com/youtube/terms/developer-policies#a.-api-client-terms-of-use-and-privacy-policies)) The Google APIs ToS §3.d has a similar clause.
- **YouTube ToS link:** "API Clients must display a link to YouTube's Terms of Service (https://www.youtube.com/t/terms), and they must also state in their own terms of use that, by using those API Clients, users are agreeing to be bound by the YouTube Terms of Service." ([Policies III.A.1](https://developers.google.com/youtube/terms/developer-policies#a.-api-client-terms-of-use-and-privacy-policies))
- **Branding and attribution:** "Any API Client page or feature that displays YouTube content – including, without limitation, search results, YouTube videos, channels, playlists, thumbnails, and YouTube players – must make clear to the viewer that YouTube is the source of the relevant content by displaying YouTube Brand Features in accordance with … the YouTube Branding Guidelines." ([Policies III.F.2](https://developers.google.com/youtube/terms/developer-policies#f.-user-experience)) Also: "All API Clients must provide proper attribution in accordance with the YouTube Branding Guidelines". ([ToS §10.3](https://developers.google.com/youtube/terms/api-services-terms-of-service#brand-features-and-attribution)) The Branding Guidelines add: "You should feature the appropriate branding logo on any page where the YouTube API has a presence", "Any YouTube logo used within an application must link back to YouTube content", and "You must never use the YouTube name or any abbreviation … in conjunction with the overall name of your application". They also describe a "developed with YouTube" logo for apps that would be "nonfunctional or not useful" without YouTube. ([Branding Guidelines](https://developers.google.com/youtube/terms/branding-guidelines#logo_sizing_and_placement))
- **Audits and monitoring (no trigger needed):** "YouTube may monitor, review and inspect your API Client(s) … at any time and without further notice". ([ToS §6](https://developers.google.com/youtube/terms/api-services-terms-of-service#api-clients-and-monitoring)) "Upon request … provide YouTube with account(s) necessary to access all features or functions of the current, in-production version(s) of your API Clients". ([Policies III.H](https://developers.google.com/youtube/terms/developer-policies#h.-monitoring-and-audits))
- **Quota extension and compliance audit (only when you need more quota):** "If your API Client reaches the quota limit for a service, you can apply for a quota extension by completing an API Compliance Audit". ([Policies III.D, Usage and Quotas](https://developers.google.com/youtube/terms/developer-policies#usage-and-quotas)) "If you would like to request additional quota beyond the default allocation, you must first complete an audit". Periodic audits happen "If you have been contacted by us". ([Quota and Compliance Audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits#periodic-audit))
- **Voluntary audit:** "If, after reviewing this article and the policies linked to above, you're unsure whether your service is allowed, please apply for an API Compliance Audit, and include a clear summary that mentions any end users in the audit form." ([Guide, intro](https://developers.google.com/youtube/terms/developer-policies-guide))
- **Contact email:** "YouTube's primary means of contacting you … is the email address that is associated with the Google Account that you use to log in to the Google Developers Console. You must comply to any communication that YouTube sends you regarding compliance issues". ([Policies III.D](https://developers.google.com/youtube/terms/developer-policies#d.-accessing-youtube-api-services))
- **Inactivity:** access can be curtailed "if your API Project has been inactive for 90 consecutive days". (Policies III.D)

### Interpretation

- **Apply literally, whoever the users are (medium-high confidence):** the privacy policy, the YouTube ToS link, the Google Privacy Policy link, and YouTube attribution on pages that show YouTube content. The text says "each API Client" and "any API Client page". The only person who has to "agree" is the developer, which makes the requirement close to a formality. But the text doesn't make it optional, and complying is cheap: a static page in the Streamlit app, plus a YouTube logo linking to YouTube next to Evidence lists. **Whether YouTube would ever enforce these against a local tool nobody else uses is unknown.** There's no public statement either way.
- **Applies only on YouTube's request:** audits, monitoring, the periodic audit form and access to the client. contention should be ready to answer these, which means keeping the email on the Cloud project monitored.
- **Applies only if more quota is needed:** the quota extension form. The spec's refresh uses ~1,300 of 10,000 daily units, so it isn't needed. It becomes relevant if the user chooses the voluntary-audit route to settle section 5.
- **Doesn't apply (high confidence), because contention doesn't use the feature:**
  - the upload notice and Made for Kids rules (ToS §9.1, Policies III.J);
  - embedded player rules (RMF, Policies III.E.4.i–j);
  - comment display rules (RMF);
  - OAuth consent, revocation and Authorized Data clauses (while there's no OAuth);
  - child-directed client rules;
  - the Change of Control form;
  - commercial and ad rules (III.G).

  The RMF sections cover only the "YouTube embedded player and video playback", "Uploading videos", comments and live chat. ([RMF](https://developers.google.com/youtube/terms/required-minimum-functionality))
- **Applies fully, with no users needed:** credential rules. "You must not … embed your API Credentials in open source projects." "you must create exactly one (1) API Project for that API Client." Also no sharding of projects "to artificially acquire more API quota". ([Policies III.D](https://developers.google.com/youtube/terms/developer-policies#d.-accessing-youtube-api-services); [Guide](https://developers.google.com/youtube/terms/developer-policies-guide#dont_spread_api_access_across_multiple_or_unknown_projects)) **The contention repository is public**, so the key must never be committed. It's currently kept in the git-ignored `.env`.

## 5. Derived data and metrics (Q4)

### The exact prohibition

[Policies III.E.4.h](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content):

> Your API Clients must not (i) replace API Data with similar, independently calculated data, or (ii) access or use API Data to create new or derived data or metrics. To the extent your API Clients display any information, data or metrics not based on API Data alongside API Data, your API Clients must include a clear and prominent disclosure there that such information, data and metrics are not from YouTube and are part of your own product.
>
> For example, when displaying the number of likes for a video, your API Client must use the number returned in the API Data. You must not substitute a different number to represent likes … Similarly, you are not permitted to use the number of likes returned in the API Data to calculate other metrics, such as the percentage of total likes that were made through your API Client or a score that factors in likes, total views, or any other API Data.

### The Guide's clarifications

Under the heading "Only offer metrics that are available via YouTube's API services" ("Don't use YouTube's API to offer independently calculated or derived metrics or data that replace or provide new data that isn't available via YouTube's API services"), the Guide gives a list of "Don't use YouTube's API to" items. ([Guide](https://developers.google.com/youtube/terms/developer-policies-guide#only_offer_metrics_that_are_available_via_youtubes_api_services)) The ones relevant to contention:

- "Infer or estimate the content category/type of a video or channel; you may only use the content type returned by the YouTube API."
- "Estimate audience affinities, demographics, or audience composition of a channel or video."
- "Calculate and assign custom 'scores' to channels based on independently calculated averages or ratios -- for example, average view count, comment count, or overall brand suitability."
- "Merge or combine YouTube API data with any other data."
- "Return information like the total number of video views and offer a number different from the number provided by YouTube's API."
- "Gamify channel performance by ranking or tracking views between different channels".
- "Gain insights into the number of users, number of videos uploaded, watch time, financial performance, or any other aspect of YouTube's business."

It also defines "Acceptable metrics": "those that use only YouTube API data and combine them via simple mathematical calculations (combine them via addition, subtraction, averages, multiplication, division). These metrics must not incorporate any other external data sources." Its examples include "Average video duration", "Total views in a group of videos/channels", and "Top viewed videos/channels sorted by views". ([Guide, Acceptable metrics](https://developers.google.com/youtube/terms/developer-policies-guide#acceptable_metrics))

### The June 2026 Derived-metrics amendment

- The Policies now say: "These policies are only applicable to audited developers with analytics use cases that have explicitly applied for permission to create additional metrics and/or store statistical data through the standard quota extension request from (starting June 01, 2026)." ([Policies III.L](https://developers.google.com/youtube/terms/developer-policies#l.-additional-policies-on-derived-metrics-and-data-storage))
- The Guide adds: "If you have not applied for this permission and/or your use case has not been approved, don't create derived metrics and/or store data beyond what is permitted in the developer policies." ([Guide](https://developers.google.com/youtube/terms/developer-policies-guide#additional_policies_for_derived_metrics_and_data_storage))
- The amendment itself: "As a developer, you are generally prohibited from creating metrics that replace or modify the data returned by the YouTube API Services. However, subject to your acceptance of the amendment … YouTube permits the calculation of specific additional metrics". To accept, select "Section 5: Use Cases, API Integration, and Feature Implementation" then "Analytics & Reporting" as your use case. "Your API Service must reflect an analytics use case on YouTube." It also says: "Violating these policies may result in API quota reduction or termination of your API access." ([Derived-metrics amendment](https://developers.google.com/youtube/terms/derived-metrics-policy))
- Among the metrics it allows (with acceptance):
  - **"Content Categorization and Tagging":** "You may use analysis to assign descriptive sub-genres or tags to videos and channels. These must be additive and distinct from YouTube's video categories". ([#categorization](https://developers.google.com/youtube/terms/derived-metrics-policy#categorization))
  - **"Custom Channel Scores and Ratios"** based on "independently calculated averages, sums, or ratios of API Data". ([#scores](https://developers.google.com/youtube/terms/derived-metrics-policy#scores))
  - **"Viewer Sentiment Analysis"**, which forbids inferring "sensitive protected attributes of the audience".
- The revision history summarises it: "Added the Additional policies on derived metrics and data storage … for audited developers with analytics use cases that have explicitly applied for permission to create additional metrics (such as custom scores, earnings estimates, suitability scoring etc.)". ([Revision history, May 4, 2026](https://developers.google.com/youtube/terms/revision-history))

### Related rules

- **Aggregation:** "Do not aggregate API Data except that you may only aggregate API Data relating to YouTube channels that are under the same content owner … Do not aggregate API Data or otherwise use API Data or YouTube API Services to gain insights into YouTube's usage, revenue, or any other aspects of YouTube's business." ([Policies III.E.2](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content)) The Guide's version narrows the first clause to "authorized API data", and lists "Total views in a group of videos/channels" as acceptable.
- **Altering API Data:** "modify, interfere with, replace, or otherwise disable any functionality, data, or content made available as part of … YouTube API Services. For example, you must not remove, obscure, alter, or disable any links that appear in … API Data." ([Policies III.I](https://developers.google.com/youtube/terms/developer-policies#i.-additional-prohibitions))
- **Proprietary rights notices:** "You will not remove, obscure, or alter … any links to or notices of those terms … or falsify or delete any author attributions". ([ToS §11](https://developers.google.com/youtube/terms/api-services-terms-of-service#proprietary-rights-notices))
- **Third parties:** "sell, purchase, lease, lend, convey, redistribute, or sublicense all or any portion of YouTube API Services" is prohibited. ([Policies III.G.1](https://developers.google.com/youtube/terms/developer-policies#g.-distribution-and-commercial-use)) You must also "protect API Data … from unauthorized access, use, or disclosure". (Policies III.E, Security)

### Interpretation, feature by feature

What the text settles:

- **The prohibition covers creating derived data, not just displaying it.** "(ii) access or use API Data to create new or derived data or metrics" has no display qualifier. ADR 0003's line (derived data follows its source, and is never shown as a YouTube statistic) handles storage and presentation. It does **not** meet the literal ban on creation. ADR 0003 already admits that "the fully literal reading … would forbid the whole project".
- **Since June 2026, YouTube has published how it reads that ban.** Categorisation and custom scores are "generally prohibited" unless the developer has been audited and accepted for an analytics use case. That makes the strict reading more authoritative than it was when ADR 0003 was written.

| contention feature | Closest text | Reading | Confidence |
|---|---|---|---|
| **Format labels** (LLM picks one Format per Video) | Guide: "Infer or estimate the content category/type of a video or channel; you may only use the content type returned by the YouTube API." Amendment allows "descriptive sub-genres or tags" **only with acceptance**. | Squarely covered. Prohibited without approval. | High |
| **Audience labels and Audience groups** | Guide: "Estimate audience affinities, demographics, or audience composition of a channel or video." | Very likely covered. An LLM sentence like "junior developers looking for their first job" is an estimate of audience composition. It doesn't infer protected attributes, which the amendment forbids even with approval. | Medium-high |
| **Themes** (clusters of Video embeddings, labelled by LLM) | Same "content category/type" item, and the amendment's "Content Categorization". | Probably covered once labelled and used as categories. Unlabelled cluster ids used only internally are less clear. | Medium |
| **Embeddings** | Not mentioned anywhere. Literally "derived data". | **Ambiguous.** An embedding is an internal representation used for search, not a metric shown to anyone. Nothing in the text separates internal processing from output, and nothing mentions search indexes. | Unclear |
| **Cleaned description text and parsed Chapters** | III.I "must not remove … links that appear in … API Data"; III.E.4.h "derived data". | Cleaning strips links and promotions. Used only as internal input, probably low risk. Showing the cleaned text *as the description* would conflict with III.I and ToS §11. | Medium (internal use); high (if displayed) |
| **Predicted log views for a Draft** | Guide: "offer a number different from the number provided by YouTube's API". The amendment allows "Financial Performance Projections" only with acceptance. | A Draft isn't a YouTube Video, so no API number is being replaced. But the prediction is a new metric computed from API Data, and it isn't "simple mathematical calculations". Not addressed directly. | Unclear |
| **Prediction errors and "did better/worse than expected"** | III.E.4.h(ii); the likes example forbids "a score that factors in likes, total views, or any other API Data". | A per-Video performance score derived from views. Fairly close to the likes-score example. | Medium-high that it's covered |
| **Prior-uploads baseline and "the Channel's typical Video at 90 days"** | Guide: "custom 'scores' to channels based on … average view count". The amendment allows "Custom Channel Scores" only with acceptance. Acceptable metrics include simple averages. | A median of log views is close to an "average view count" per channel. As an internal model feature it's unclear. Shown to the user as the Channel's typical performance, it is close to a channel score. The Guide's "acceptable metrics" list may cover a plain average of API views (no external data). A median of logs isn't on the list but is similar. | Unclear |
| **Group stats** (counts and gaps per Theme, Format and so on) | III.E.2 aggregation; Guide "acceptable metrics" (totals and averages over groups). | Simple counts over public data look like the Guide's acceptable metrics. But they're grouped by derived labels and use derived errors, so they inherit those problems. | Unclear |
| **Sending titles and descriptions to Claude or OpenRouter** | III.G.1 "convey, redistribute"; III.E security "unauthorized … disclosure"; Guide "Merge or combine YouTube API data with any other data". | Not addressed. Sending data to a model provider that processes it on your behalf is arguably use, not redistribution. A free model provider that logs or trains on prompts is harder to defend. | Unclear |

**Bottom line (no guesswork):**
- The text *clearly* reaches Format labels, and very probably Audience labels.
- It *probably* reaches the "better/worse than expected" per-Video scores and user-facing channel baselines.
- It is *silent or ambiguous* on embeddings, clusters used only internally, and predictions for Drafts.
- The only route the documents offer to do the covered things with explicit permission is the audited Analytics & Reporting use case under the Derived-metrics amendment.

## 6. Enforcement: what can be suspended or terminated (Q5)

### What the text says

- **ToS §3.1:** "YouTube may suspend or terminate your access to, or use of, any aspect of the YouTube API Services (including any credentials assigned to you or your API Client(s)), impose additional requirements and restrictions, or terminate the Agreement between you and YouTube, for any violation of the Agreement by you, your API Client(s) or those acting on your behalf." ([ToS §3](https://developers.google.com/youtube/terms/api-services-terms-of-service#permitted-access))
- **ToS §24.2:** "YouTube reserves the right to (i) suspend or terminate access to, or use of, any aspects of the YouTube API Services by you, your API Client(s) and those acting on your behalf), and (ii) terminate the Agreement … at any time. For example, we may need to exercise such rights in instances of your breach of this Agreement, court order, when we believe there to have been misconduct … Although we will try to give you reasonable notice, we have no obligation to do so." ([ToS §24](https://developers.google.com/youtube/terms/api-services-terms-of-service#termination))
- **ToS §24.3:** "Upon any suspension, notice of any discontinuance, or termination … you will immediately stop accessing and using all YouTube Property and delete all YouTube API Services (including all API Data) … At YouTube's request, you will certify your deletion … in writing". Also: "YouTube may independently communicate with any account owner whose account(s) are associated with credentials assigned to you".
- **Guide:** "Violating any of these policies may result in reduction of your API quota, revoking your API keys and their associated privileges, or other actions, including termination of the Google account associated with the API service found to be in violation." ([Guide, intro](https://developers.google.com/youtube/terms/developer-policies-guide))
- **Derived-metrics amendment:** "Violating these policies may result in API quota reduction or termination of your API access."
- **Policies III.D, Prohibited Access:** "You are prohibited from accessing or attempting to access YouTube API Services via any means if your API Credentials are suspended, revoked, or terminated, or if the Google Account you used to create those credentials is suspended or terminated, for any reason. In that case, you must not access or attempt to access YouTube API Services via any means, including by creating or using a proxy to create new Google Accounts, API Credentials or API Projects." ([Policies III.D](https://developers.google.com/youtube/terms/developer-policies#d.-accessing-youtube-api-services))
- **Policies III.D, Inactivity:** "YouTube could revoke your API Credentials, or reduce (or eliminate) your API Project's quotas".
- **ToS §25.9:** project ids can "automatically terminate" after an unapproved change of control. (Not relevant here.)
- **Google APIs ToS §3.a:** "Google may suspend access to the APIs by you or your API Client without notice if we reasonably believe that you are in violation of the Terms." **§8.a:** "Google reserves the right to terminate the Terms with you or discontinue the APIs or any portion or feature or your access thereto for any reason and at any time". **§2.b:** "You will not violate any other terms of service with Google (or its affiliates)." ([Google APIs ToS](https://developers.google.com/terms))
- **Google Terms of Service:** "Google may suspend or terminate your access to the services or delete your Google Account if any of these things happen: you materially or repeatedly breach these terms, service-specific additional terms, or policies; … we reasonably believe that your conduct causes harm or liability to a user, third party, or Google — for example, by … scraping content that doesn't belong to you". ([Google ToS, "Suspending or terminating your access to Google services"](https://policies.google.com/terms))

### Interpretation

**Q5 answer.** The documents name these targets, from narrowest to widest:
1. **Quota:** reduction or elimination.
2. **API key and credentials:** revocation.
3. **The API Project and the Agreement:** termination, with a duty to delete all API Data and, if asked, certify it in writing.
4. **The Google account** "associated with the API service". The Guide names this explicitly.

Google account termination under the Google Terms of Service means losing access to "the services" generally: Gmail, Drive, YouTube and so on on that account. *Confidence:* high that it's within the stated powers. Whether YouTube's API team actually escalates to account termination for a low-volume, non-distributed tool is **not documented**. The documented escalation path (audits, "comply to any communication", appeals) suggests contact before termination is normal. But the ToS says notice is not guaranteed ("we have no obligation to do so").

*Interpretation (medium confidence):* the blast radius is smaller if the Cloud project and API key live under a **dedicated Google account** that doesn't hold the user's personal email or data. Doing this from the start isn't "masking identity" (III.D), as long as the account is truthfully the developer's. What is forbidden is creating new accounts or projects *after* a suspension to regain access. Keep exactly one API Project for contention.

## 7. Compliance checklist

Current status comes from `docs/spec/mvp.md`, ADRs 0001–0007 and the `issue-27-collect-channels` branch. **The purge job isn't built yet ([#28](https://github.com/Jarrod-Bob/contention/issues/28)).**

| # | Requirement (source) | Applies to contention? | Current status | Action needed |
|---|---|---|---|---|
| 1 | Non-Authorized Data, ids included, deleted or refreshed within 30 days (III.E.4.d) | Yes | Designed: 28-day purge, weekly refresh, `ON DELETE CASCADE` from Videos and Channels. Not built (#28). | Build #28. Include the startup purge. Make the job fail loudly if the last successful refresh is older than ~21 days. |
| 2 | Statistics not stored past 30 days (III.E.4.b) | Yes | Snapshots kept ≤28 days by design. Not built (#28). | Cover in #28. Test that no statistic survives past 28 days in any table. |
| 3 | Derived data follows its source (ADR 0003's line; III.E.4.d with III.E.4.h) | Yes | Designed for DB rows. Not designed for artefacts outside Postgres. | Put the persisted artefacts under the same ≤28-day rule: LightGBM/CQR model files, cluster centroids, BM25 indexes, saved numpy matrices, Streamlit caches, logs, LLM traces and batch outputs, DB dumps. Or don't persist them. |
| 4 | Ids get no 30-day exemption | Yes | Handled: ADR 0001 keeps ids out of the niche folder. The niche folder holds user-typed handles and Tiers. | Keep `channels add` from writing API-sourced values (channel ids, titles, computed Tiers) into the committed niche folder. |
| 5 | "Limited amounts" of Non-Authorized Data (III.E.4.d) | Unclear | ~15–30k Videos planned. | None required. Mention the Corpus size if you ever apply for an audit. |
| 6 | Stored data kept consistent; latest data displayed; historical data shown "in context of time" (III.E.4.e–f) | Yes | Weekly refresh. Evidence shows title and link. | Show Evidence from the latest refresh. Label any Snapshot-based number with its date. |
| 7 | No creating new or derived data or metrics (III.E.4.h; Guide; III.L) | Yes. Covers Format labels (clearly), Audience labels (very likely) and per-Video performance scores (probably). Unclear for embeddings, internal clusters and Draft predictions. | Not compliant under the strict reading for Format and Audience labels, Themes as categories, "did better/worse than expected" and "Channel's typical Video". | **Decide, and record in a new ADR superseding the relevant part of ADR 0003.** Options: (a) apply for the API Compliance Audit with the Analytics & Reporting use case to accept the Derived-metrics amendment; (b) redesign to drop or replace the covered features; (c) knowingly accept the risk. See the note below the table. |
| 8 | Derived data never presented as YouTube data; non-YouTube metrics clearly disclosed (III.E.4.h, second sentence; III.F.2 "must not be shown in a way that suggests that the content is originating from YouTube") | Yes | Designed ("never as a YouTube statistic"). | In the UI, label predictions, labels, Themes and group stats "computed by contention, not from YouTube". |
| 9 | Don't alter API Data or strip its links when presenting it (III.I; ToS §11) | Yes, if descriptions are displayed | Cleaned text is used for embeddings and labelling. Display isn't specified. | Use cleaned text only internally. Wherever a description is shown, show the original. |
| 10 | Aggregation limits and no insights into YouTube's business (III.E.2) | Unclear (the Guide narrows it to Authorized Data) | Group stats over public Videos. | Keep group stats to simple counts and averages. Don't compute platform-level insights. Revisit together with row 7. |
| 11 | API Data shared with third parties (III.G.1 "convey, redistribute"; III.E security "unauthorized … disclosure") | Unclear | Titles and descriptions go to Claude, and to free OpenRouter models while building and for eval judging and pre-grading. | Prefer local models or providers that don't train on or keep inputs. Avoid free OpenRouter models whose providers log or train on prompts for API Data. |
| 12 | Privacy policy that users agree to, which says the client uses YouTube API Services and links the Google Privacy Policy (ToS §7; III.A.2; Google APIs ToS §3.d) | Yes by the literal text (no single-user carve-out); enforcement against a local tool is unknown | None. | Add a short privacy page in the Streamlit app and README: what it fetches and stores, the 28-day deletion, "uses YouTube API Services", and a link to http://www.google.com/policies/privacy. |
| 13 | Link to YouTube ToS and state users are bound by it (III.A.1) | Yes (literal) | None. | Add the link and the sentence to the same page and the README. |
| 14 | YouTube attribution on pages that show YouTube content; logo links to YouTube; no "YouTube"/"YT" in the app name (III.F.2; ToS §10.3; Branding Guidelines) | Yes (literal) | None. The name "contention" is fine. | Add a "developed with YouTube" logo, linked to YouTube, on the Strategist and Optimiser pages next to the Evidence. Follow the logo rules. |
| 15 | No scraping and no undocumented APIs; only the API used to retrieve API Data (III.E, Scraping; III.D, Undocumented Services; III.I) | Yes | Compliant: API only, no transcripts (ADR 0004). | Keep it that way. Don't fetch thumbnails or pages outside the API. |
| 16 | No audiovisual download or storage (III.E.1) | Yes | Compliant: text only. | None. |
| 17 | Credentials: not embedded in open-source projects; exactly one API Project per client; no quota sharding (III.D; Guide) | Yes | `.env` is git-ignored. The repo is **public**. One project assumed. | Keep the key out of git (a pre-commit secret scan is cheap). Restrict the key to the YouTube Data API in Cloud Console. Use one project only. |
| 18 | Don't exceed or circumvent quota (ToS §15) | Yes | ~1,300 of 10,000 units per refresh. | None. |
| 19 | Keep the contact email monitored and respond to compliance communications (III.D) | Yes | Unknown. | Make sure the Cloud project's Google account email is one you read. |
| 20 | Monitoring and audits on request (ToS §6; III.H) | Yes, on request | N/A until contacted. | Respond within the stated timeframe if contacted. |
| 21 | Quota extension or compliance audit form (III.D; Audits page) | Only for more quota, or voluntarily (the Guide invites it when unsure) | Not needed for quota. | Optional: use it to settle row 7 (option a). |
| 22 | Inactivity: 90 days may lose quota or credentials (III.D) | Yes | Weekly refresh keeps the project active. | None. |
| 23 | On suspension or termination, stop, delete all API Data and certify (ToS §24.3; III.D Prohibited Access) | Yes, if it ever happens | N/A. | Keep deletion to a single command (drop the database, delete artefacts). Never create new accounts or projects to get around a suspension. |
| 24 | Limit the blast radius on the Google account (the Guide names account termination) | Yes (risk management, not a policy requirement) | Unknown which account owns the project. | Consider hosting the Cloud project under a dedicated Google account from the start (see section 6). |
| 25 | Uses the most recent API versions and can be updated (III.B) | Yes | Data API v3. | Watch the [revision history](https://developers.google.com/youtube/terms/revision-history) (it has an RSS feed). |
| 26 | Authorized Data rules: consent scopes, revocation, deletion in 7 or 30 days, 30-day re-verification, Authorized-Data privacy clauses (III.A.2.h–i; III.D; III.E.3–4) | No (no OAuth; creator analytics out of scope) | N/A. | If OAuth is ever added, apply section 3 in full. |
| 27 | Upload notices, Made for Kids, embedded player and RMF, comments, child-directed clients, ad and commercial rules (ToS §9; III.C; III.E.4.i–j; III.F.3; III.G; III.J; RMF) | No | N/A. | None, unless an embed or thumbnails are added. Embeds would bring in the RMF player rules. |
| 28 | Don't publish derived findings or data (III.G.1 redistribute; III.E.4.h) | Yes | Nothing is published. | Keep eval reports and portfolio write-ups free of API Data, such as specific Videos' metrics or labels. Aggregate scores only. |

**On row 7.** Once the June 2026 amendment exists, the least risky option for the user's Google account is either:
- **(a) Ask YouTube.** File the audit form with the Analytics & Reporting use case, describing contention honestly as a single-user, local analytics tool.
- **(b) Redesign.** For example: use YouTube's own `categoryId` and `topicDetails` instead of LLM Format and Audience labels on Corpus Videos; keep LLM inference only for the user's own Drafts, which aren't API Data; stop showing per-Video "better/worse than expected" and channel baselines.

Option (a) invites scrutiny and may be refused. Option (b) removes core parts of the project's learning goals (ADR 0006's group stats depend on Format, Audience and Themes). Option (c), carrying on as designed, means relying on a reading that the published Guide contradicts for at least Format and Audience labels. This is the user's call.

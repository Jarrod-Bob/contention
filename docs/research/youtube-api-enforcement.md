# How YouTube enforces its API policies against small tools

Research for [#44](https://github.com/Jarrod-Bob/contention/issues/44), part of the map in [#43](https://github.com/Jarrod-Bob/contention/issues/43). It follows up [the policies research note](https://github.com/Jarrod-Bob/contention/blob/research/youtube-developer-policies/docs/research/youtube-developer-policies.md), which set out what the YouTube API Services Terms and Developer Policies *say*. This note asks what enforcement *looks like in practice*, to calibrate the "knowingly accept the risk" option for contention's derived data.

contention's profile, for comparison: single user, runs locally, not distributed, YouTube Data API v3 with an API key only (no OAuth), public data only, about 1,300 units a week against a 10,000-unit daily default, code in a public GitHub repo.

**Every case below is anecdotal.** They are self-reports by developers (Stack Overflow, Google's issue tracker, Google's developer forum, GitHub issues, Hacker News, blog posts) or press coverage. None is confirmed by Google, and most give only one side. Sources were read on **2026-09-27**.

## TL;DR

1. **Evidence is thin, and almost all of it comes from apps that either had users or asked for more quota.** I found no public case of enforcement against a key-only, public-data, low-volume personal tool that never applied for a quota extension and never hit its quota. That is an absence of reports, not proof that it doesn't happen.
2. **The usual pattern is an email first, then a quota cut.** In nearly every case with detail, YouTube first emailed a "mandatory compliance review" or audit request with a 3 to 7 business-day deadline, then cut quota (often to 0) if there was no adequate reply. Silent drops to 0 are also reported often, but in many of those the developer had just applied for more quota, or the project had been inactive, or the developer later found a missed email.
3. **The most common trigger is applying for a quota extension.** Applying opens a compliance review, and several developers report their quota going *down* (to 0) after applying. Second is the 90-day inactivity rule. Third is YouTube-initiated periodic audits, which seem to target projects with real usage or users.
4. **Storage and derived-data rules do appear in findings, but only inside reviews the developer had already triggered.** Two issue-tracker reports (2022, 2023) quote a "ToS Violation Report" that flagged storing API data for three months against the 30-day rule. Both came up during a quota extension request. I found no case where derived data or storage alone triggered enforcement out of the blue.
5. **Nothing public yet after the June 2026 derived-metrics amendment.** Two Google developer-forum threads from July to September 2026 show the review process still running (slow replies, a solo developer's quota stuck at 0 after being approved), but neither involves derived metrics. It is too early and too quiet to say how the amendment is enforced.
6. **No documented case of a whole personal Google account being terminated over YouTube API policy.** The Developer Policies Guide says it can happen. The only claim I found is a one-line, unexplained 2016 GitHub issue. The documented actions are quota cuts, key or project access being disabled, and in a few cases a final refusal with no reasons given.

## How the evidence was gathered

- Stack Overflow, via the Stack Exchange API, searching the `youtube-api` tag for "quota reduced", "quota 0", "compliance audit", "audit form", "ToS violation", "api key revoked" and "derived". Google's own [support page](https://developers.google.com/youtube/v3/support) points developers to Stack Overflow, so this was the main public channel until about 2022. Very few relevant questions appear after 2023.
- Google Issue Tracker, component 186600 (YouTube API Service), via web search plus the public JSON for each issue.
- Google Developer forums (discuss.google.dev), via their search API.
- GitHub issues (`gh search issues`), Hacker News (Algolia API), and general web search for news and blogs.
- Reddit: web searches restricted to reddit.com returned nothing relevant. **Reddit is not covered**, which is a real gap.

## Cases

Grouped by what happened. "Notice first?" means whether the developer says they got an email or audit request before the action.

### A. Quota cut after an ignored or incomplete audit request

| Date | Who / what | What happened | Trigger | Notice first? | Storage or derived data? | Source |
|---|---|---|---|---|---|---|
| Feb 2020 | Individuals running a **personal Google Apps Script** that syncs subscriptions into playlists ([auto-youtube-subscription-playlist-2](https://github.com/Elijas/auto-youtube-subscription-playlist-2)) | Several users got "mandatory compliance review" emails. One (MrNgL) got a reminder on Feb 18 giving "3 days to respond". He filled in the audit form as a private individual ("organization: none"), with a screenshot of his sheet, and on Mar 12 was told the review was complete with "no further actions". Another (Fabian42) filled the form with "-" in most fields and says YouTube then "disabled my access to the YouTube API completely". He set the script up again in a new project, which worked. A third said "I filled it out and it was fine". | Unknown. The emails don't say why. One user guessed that hitting the quota often (about 900 channels) flagged it. | Yes, email plus reminder. | No. | [GitHub issue #68](https://github.com/Elijas/auto-youtube-subscription-playlist-2/issues/68) |
| Feb 2020 | [youtube-viewer](https://github.com/trizen/youtube-viewer), an open-source CLI client with a shared default key used by many people | Email: "we have sent multiple reminders, which required you to submit a completed Audit Form … As a result we have reduced your quota access to YouTube Data API. You have three (3) days to respond". Quota cut from 25M to 12.5M a day, then the default key was disabled. Users were told to create their own keys. | Periodic audit of a high-quota shared key. | Yes, multiple reminders. | No. | [youtube-viewer #308](https://github.com/trizen/youtube-viewer/issues/308) |
| Jun 2023 | Author of a "small personal application with minimal revenue" | Quota reduced to the default allocation after YouTube demanded an audit. The author says repeated audit submissions went unanswered. | Audit demand. The reason isn't stated. | Yes. | Not stated. | [Williamsport Web Developer blog](https://williamsportwebdeveloper.com/cgi/wp/?p=4254) |
| Jul 2020 | Web app using 25k to 300k queries a day | "after receiving several emails alerting that I had to do an Audit, the queries for the day stopped completely." The audit then passed, but quota stayed at 0 for about a month. | Audit. | Yes. | Not stated. | [SO 62716847](https://stackoverflow.com/questions/62716847) |
| Jun 2020 | App developer | "My YouTube API access was disabled and I was asked to submit the YouTube audit form." After passing, still got `accessNotConfigured`. | Audit. | Unclear whether access was cut before or after the request. | Not stated. | [SO 62426607](https://stackoverflow.com/questions/62426607) |

The verbatim audit email (Aug 2019) asked for "A fully functional demo account … A fully completed Youtube API Audit Form … Screenshots … Documents relating to your implementation" within "seven (7) business days" ([SO 57409393](https://stackoverflow.com/questions/57409393); legitimacy confirmed by another recipient in [SO 57495538](https://stackoverflow.com/questions/57495538)).

### B. Quota cut to 0 after applying for more quota

| Date | Who / what | What happened | Notice first? | Storage or derived data? | Source |
|---|---|---|---|---|---|
| Mar 2019 | App in development | Quota went to 0 after a quota increase request. "no warnings, or anything really." | No (by their account) | Not stated | [SO 55396018](https://stackoverflow.com/questions/55396018) |
| May 2019 | App about to launch | Quota went to 0 "three days later" after requesting an increase, "without any clear explanation". An answer suggests they missed emails. | Disputed | Not stated | [SO 56221425](https://stackoverflow.com/questions/56221425) |
| Sep 2019 | "harmless small startup", 4 years on the API | Quota went from 640,000 to 0 after asking for more, "without any warning". Two days later an email cited Policy I.1 (Additional Prohibitions). | No; the reason came after | Not stated | [SO 58043776](https://stackoverflow.com/questions/58043776) |
| Nov 2019 | Developer | "I applied for a YouTube Data API quota increase, and now my quota was set to 0, without a word from YouTube." | No | Not stated | [SO 59054045](https://stackoverflow.com/questions/59054045) |
| Aug 2020 | Indie app (playsiv.com) | After months of back and forth on a quota request, the key was revoked for "reverse engineering" the API. | Yes (long review) | No (undocumented-API use suspected) | [SO 63218685](https://stackoverflow.com/questions/63218685) |
| Jul 2022 | Web service "WeSub" | A quota extension request produced a "ToS Violation Report" citing `store_youtube_api_length: three months` and `refresh_youtube_api_rate: one day`. | Yes (report during review) | **Yes: storage past 30 days** | [Issue tracker 239455625](https://issuetracker.google.com/issues/239455625) |
| Jun 2023 | albaberlin.de (agency) | "We received ToS Vioaltion Report … violation about storing API data for more than 30 days. In report there is a screenshot that variable store_youtube_api_length: three_months." The developer says they never set this. The value probably came from their own audit-form answers. | Yes (report) | **Yes: storage past 30 days** | [Issue tracker 289237743](https://issuetracker.google.com/issues/289237743) |

Neither storage report says quota was cut. They are findings the developer was asked to fix inside a review they had started.

### C. Quota cut to 0 with no stated reason (often inactivity)

| Date | What happened | Notice first? | Source |
|---|---|---|---|
| Nov 2017 | Long-used project suddenly got `accessNotConfigured`, quota 0. A later answer quotes a Googler on the issue tracker: quota 0 "means that your project's access to YouTube Data API Service has been disabled. You should've received a notice via email". | Probably (per Google) | [SO 47099012](https://stackoverflow.com/questions/47099012) |
| Nov 2018 – Mar 2019 | Emails "FYI, YouTube may disable your inactive project(s)" (Nov 9, 2018) and "[Final notice] …" (Dec 13, 2018), then all keys stopped working and quota was locked at 0, although the developer says the projects were active. Fix: re-enable form, or a new project. | Yes, two emails | [SO 54990432](https://stackoverflow.com/questions/54990432) |
| Nov 2018 | WordPress plugin author got the 60-day inactivity warning because caching meant the project made few API calls. Clearing the cache fixed it. | Yes | [futtta.be blog](https://blog.futtta.be/2018/11/10/lyte-youtube-api-use/) |
| Jun 2021 | Quota went from 37M to 0 "for no apparent reason". "no warnings or notifications". | No (by their account) | [SO 68035151](https://stackoverflow.com/questions/68035151) |
| Dec 2021 | Key unused for about a year, quota now 0. | Unknown | [Issue tracker 211012781](https://issuetracker.google.com/issues/211012781) |
| May 2022 | Small management site showing video view counts. Daily quota became 0 and couldn't be edited. | Not stated | [SO 72224382](https://stackoverflow.com/questions/72224382) |
| May 2022 | A long-time answerer (not a Googler) says "My contacts at google have been unclear why some projects get their quota removed" and that he has had brand-new projects start at 0. A second new project got 10k. | n/a | [SO 72355518 answer](https://stackoverflow.com/a/72359522) |
| Nov 2024 | New project shows 0 queries a day, not the documented 10,000. | n/a | [Issue tracker 378787474](https://issuetracker.google.com/issues/378787474) |
| **Sep 2026** | **Solo developer, "personal educational website"**. Quota stuck at 0 even though the compliance review was "completed and approved twice". The request form's Submit button hangs. Another user replied "Exactly similar issue" (Sep 21). | Review happened; why quota is 0 is unknown | [discuss.google.dev 398232](https://discuss.google.dev/t/youtube-api-quota-stuck-at-0/398232) |

The workaround reported most often for a zeroed project is to create a new project. That may conflict with the Developer Policies ("exactly one (1) API Project" per API Client, and no new projects when credentials are suspended), so it is not a safe fix for contention if the zeroing was deliberate.

### D. API access revoked or threatened, with users involved

| Date | Who / what | What happened | Notice first? | Storage or derived data? | Source |
|---|---|---|---|---|---|
| Nov 2019 | CaptionPop, indie language-learning site | Months-long audit. Cited III.F.1.a (look and feel) and III.I.6 (player modification). YouTube threatened to cut access "in a couple of days". | Yes (audit) | No (embedded player) | [HN 21500874](https://news.ycombinator.com/item?id=21500874) |
| Dec 2021 | Startup (anonymous HN comment) | High quota approved after months, then "API access revoked a week later … told me it was a final decision." | Review, but no reason for the revocation | Not stated | [HN 29663733](https://news.ycombinator.com/item?id=29663733) |
| Jul 2024 | Podcast-to-YouTube service (anonymous HN comment) | Months of review, launched, "got a few videos uploaded … and they disabled my API key." Only boilerplate replies. | Review, but no reason for the revocation | Not stated | [HN 41122250](https://news.ycombinator.com/item?id=41122250) |
| Aug 2024 | Web app (anonymous HN comment) | "flagged for some bullshit" in an audit. Hid the feature from logged-out users and passed. | Yes (audit) | Not stated | [HN 41135547](https://news.ycombinator.com/item?id=41135547) |
| Jun 2025 | HIVIEW, Korean YouTube analytics platform | Compliance review findings included adding "disclaimers for independently calculated metrics" and fixing a "number of likes" metric label. Weeks without a final answer. No enforcement reported. | Yes (review) | **Yes: derived metrics labelling** (before the amendment) | [discuss.google.dev 191198](https://discuss.google.dev/t/urgent-youtube-api-compliance-audit-no-response-after-critical-deadline-launch-in-jeopardy/191198) |
| **Jul–Aug 2026** | App using upload and analytics scopes, pre-launch | "ToS Violations Report V.1" on Jul 7 with two findings: III.D.1c (project numbers) and III.F.2a,b (branding). Fixed within the 7-business-day window. More than four weeks of silence after. | Yes (they submitted the form) | No | [discuss.google.dev 388185](https://discuss.google.dev/t/youtube-api-compliance-review-silent-for-4-weeks-after-remediation-4-unanswered-follow-ups-pii-removed-by-staff/388185) |

### E. Actions outside the API process (for context)

- **Invidious, June 2023:** YouTube sent a cease-and-desist to the open-source alternative front end, citing the API Terms (privacy policy, RMF, "mimic or replicate core user experiences") and giving 7 days. Invidious doesn't use the API and ignored it. This was a legal letter, not an API action. ([TorrentFreak](https://torrentfreak.com/youtube-orders-invidious-privacy-software-to-shut-down-in-7-days-230609/), [Vice](https://www.vice.com/en/article/youtube-tells-open-source-privacy-software-invidious-to-shut-down/))
- **Musi, 2024:** Apple removed the app after complaints including YouTube's claim that it broke the API terms. Musi says it doesn't use the API. This went through the App Store, not API enforcement. ([Digital Music News](https://www.digitalmusicnews.com/2024/09/27/youtube-wrapper-app-musi-finally-pulled-from-the-app-store/))

Both targeted widely used consumer apps that stripped ads or replaced the player. Neither is comparable to contention.

### F. Whole Google account terminated

- **The one claim found:** [youtube/api-samples #66](https://github.com/youtube/api-samples/issues/66) (April 2016), titled "Why did you ban my account for using YouTube APIs?", with the body "Account was banned. When will this be reactivated?" There are no details, no replies and no way to check whether "account" means the Google account, a YouTube channel or API access. **Treat it as unverified.**
- A Hacker News case about a Google developer account terminated for being "associated" with a banned person ([HN 30855065](https://news.ycombinator.com/item?id=30855065), 2022) is about **Google Play**, not the YouTube API.
- Searches for Google accounts disabled over YouTube API use found only general account-disable help pages and YouTube channel terminations for spam (which is about content and upload behaviour, not API policy).

**Conclusion: no documented case of a personal Google account being terminated for breaking the YouTube API policies.** The power is written into the Guide ("including termination of the Google account associated with the API service") and the Google Terms, but I found no example of it being used. Because account terminations are often reported vaguely, or not at all by people who can't post from their lost account, this gap means less than it seems.

## Patterns (interpretation, medium confidence)

1. **Enforcement shows up through the audit process.** Nearly every detailed case starts with the developer submitting a quota or audit form, or with YouTube emailing a "mandatory compliance review". Findings are then numbered policy citations ("ToS Violations Report") with a 7-business-day window to fix.
2. **The main thing that exposes a project is quota.** Asking for more quota, using a lot of it (shared keys with tens of millions of units), or using none for 90 days all appear as triggers. The Feb 2020 personal-script case is the closest to contention. It shows YouTube *does* audit individuals' personal projects, at least ones that often hit the default quota, and that an honest "personal use only" answer on the form was accepted.
3. **Silent zeroing happens, and nobody outside Google knows why.** Many reports of quota at 0 with no email are unexplained. Some are probably missed emails, some inactivity, some possibly glitches or new-project defaults.
4. **Derived-data and storage findings appear only as audit findings.** The storage cases (2022, 2023) and the metric-labelling case (2025) were caught because the developer described their system on a form, or reviewers looked at a live app. None suggests YouTube detects storage or derived data from API traffic alone. That would be hard to do: a key-only client's requests look the same whatever it does with the data afterwards.
5. **Reviews are slow and replies are poor.** 2025–2026 posts complain of weeks of silence. If contention ever needs YouTube to reverse something, expect delay.

## What this means for the accept-the-risk option

### Evidence

- No public report of enforcement against a key-only, low-volume, local personal tool that never asked for more quota.
- Personal projects *have* been audited (2020 Apps Script case). One was cleared after an honest form. One reportedly lost access after a dismissive, mostly blank form.
- The usual sequence in documented cases is: email, a deadline of a few days, then quota reduction or access disabled. Silent zeroing is also reported, with no reason given.
- Storage-limit breaches have been flagged, but only when the developer's own audit answers or app revealed them, inside a review they started.
- No documented Google-account termination for API policy, and nothing yet about enforcement of the June 2026 amendment.

### Interpretation (not evidence)

- **The most likely bad outcome is losing the project's quota, not the Google account.** Based on the cases, the realistic worst case for contention is quota set to 0 or a disabled key, likely after an email with a few days' deadline. Account termination is allowed by the text but has no public track record. That lowers the likelihood in practice, but not to zero. A loss of the account would still be severe, so this is low likelihood with high impact, not no risk.
- **contention's profile avoids the documented triggers**, provided it:
  - stays well under the default quota (~1,300 units a week is about 2% of one day's quota), so never asks for an extension;
  - runs at least once every 90 days, so the project isn't flagged as inactive;
  - never commits the key to the public repo;
  - keeps one project.
- **Applying for the Analytics & Reporting amendment is the step most likely to expose contention's derived data.** The only route to approval is the quota and audit form, and the documented storage and derived-metric findings all came from exactly that process. Applying swaps an unobserved risk for a certain review, and some reviews have ended in quota cuts.
- **Being audited is what would expose derived data.** If YouTube ever emails a compliance review, answering honestly would disclose the derived labels, embeddings and stored history. The cases suggest a timely, honest answer, and then fixing or deleting what's flagged, is what keeps a project alive. Ignoring or brushing off the request is what gets it cut. So accepting the risk should include a plan: watch the Cloud project's contact email, and know in advance what contention would delete or change if asked.
- **Separating the project from the main Google account limits the worst case.** Running the Cloud project under a separate Google account used only for this tool would contain any action to that account. Whether this looks like evasion under Policies III.D depends on intent. It's a single project, not sharding, and it isn't used to get around a suspension. This is a judgment call, not something the evidence settles.
- **Confidence is low overall.** The evidence is self-selected (people post when something goes wrong), mostly from 2017–2023, mostly from apps with users, and has nothing on the post-June-2026 regime. It can rule out "enforcement against tiny tools is common and visible". It cannot rule out quiet enforcement that nobody reported.

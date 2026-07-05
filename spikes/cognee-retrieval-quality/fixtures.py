"""Adversarial fixture set for the Cognee retrieval-quality spike.

20 hand-built cases (10 false-friend pairs... actually 5 false-friend pairs +
5 disguised-twin pairs = 20 cases) spanning the Debugging and Testing
branches, per Slice 0 / PRD `.scratch/framework-retrieval-system/PRD.md`.

- false_friend: lexically similar surface wording, but the correct Framework
  differs between the two cases in the pair (tests whether Cognee is fooled
  by surface similarity).
- disguised_twin: lexically dissimilar surface wording, but both cases in the
  pair need the *same* Framework (tests whether Cognee sees past wording to
  structural similarity).

Each case carries both the raw problem text and a hand-written 4-field
Problem Abstraction schema (symptom, reproducibility, evidence_available,
goal_shape), so retrieval can be run against either representation to
isolate embedding-space failures from missing-abstraction failures.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FixtureCase:
    id: str
    kind: str  # "false_friend" | "disguised_twin"
    pair_id: str
    branch: str  # "debugging" | "testing"
    raw_text: str
    symptom: str
    reproducibility: str
    evidence_available: str
    goal_shape: str
    correct_framework: str

    def abstracted_text(self) -> str:
        return (
            f"Symptom: {self.symptom}. "
            f"Reproducibility: {self.reproducibility}. "
            f"Evidence available: {self.evidence_available}. "
            f"Goal: {self.goal_shape}."
        )


FIXTURES: list[FixtureCase] = [
    # --- FF-1: "checkout 500 error" ---
    FixtureCase(
        id="ff1-a",
        kind="false_friend",
        pair_id="ff1",
        branch="debugging",
        raw_text=(
            "The checkout page started throwing a 500 error sometime this week; it was "
            "working fine two weeks ago and I have a list of every deploy in between."
        ),
        symptom="checkout page returns 500, previously worked",
        reproducibility="deterministic",
        evidence_available="ordered deploy/commit history to bisect across",
        goal_shape="root-cause: find which change introduced the regression",
        correct_framework="binary_search_bisection",
    ),
    FixtureCase(
        id="ff1-b",
        kind="false_friend",
        pair_id="ff1",
        branch="debugging",
        raw_text=(
            "The checkout page throws a 500 error for some users but not others, on the "
            "same build, and there's no obvious pattern to who's affected."
        ),
        symptom="checkout page returns 500 for some users, same build",
        reproducibility="intermittent, depends on unknown user attribute",
        evidence_available="error reports only, no isolated trigger yet",
        goal_shape="root-cause: identify which of several plausible causes is responsible",
        correct_framework="differential_diagnosis",
    ),
    # --- FF-2: "editing article, public page doesn't show update" ---
    FixtureCase(
        id="ff2-a",
        kind="false_friend",
        pair_id="ff2",
        branch="debugging",
        raw_text=(
            "After I edit an article, the public page still shows the old text for a "
            "couple minutes, then it updates on its own."
        ),
        symptom="public page shows stale article text, self-corrects after a delay",
        reproducibility="intermittent, resolves after waiting",
        evidence_available="user observation only",
        goal_shape="fix: ensure the display updates promptly after a write",
        correct_framework="cache_invalidation_checklist",
    ),
    FixtureCase(
        id="ff2-b",
        kind="false_friend",
        pair_id="ff2",
        branch="debugging",
        raw_text=(
            "After a recent deploy, editing an article no longer updates the public page "
            "at all — it used to update instantly last sprint."
        ),
        symptom="public page never updates after edit, previously worked",
        reproducibility="deterministic",
        evidence_available="ordered deploy history to bisect across",
        goal_shape="root-cause: find which change introduced the regression",
        correct_framework="binary_search_bisection",
    ),
    # --- FF-3: "testing the discount calculator totals" ---
    FixtureCase(
        id="ff3-a",
        kind="false_friend",
        pair_id="ff3",
        branch="testing",
        raw_text=(
            "We want to make sure the discount calculator handles cart totals of exactly "
            "$0, exactly the max allowed $10,000, and one cent over the max."
        ),
        symptom="uncertain edge-value handling in a numeric range",
        reproducibility="not applicable (test design, not a bug report)",
        evidence_available="known min/max bounds of the input range",
        goal_shape="coverage-increase: cover exact edges of the allowed range",
        correct_framework="boundary_value_analysis",
    ),
    FixtureCase(
        id="ff3-b",
        kind="false_friend",
        pair_id="ff3",
        branch="testing",
        raw_text=(
            "We want to make sure the discount calculator is tested for gift-card "
            "totals, credit-card totals, and store-credit totals, since they follow "
            "different rounding rules."
        ),
        symptom="uncertain handling across distinct payment-method categories",
        reproducibility="not applicable (test design, not a bug report)",
        evidence_available="known distinct input categories, each with its own code path",
        goal_shape="coverage-increase: one representative test per input category",
        correct_framework="equivalence_partitioning",
    ),
    # --- FF-4: "testing video pause behavior" ---
    FixtureCase(
        id="ff4-a",
        kind="false_friend",
        pair_id="ff4",
        branch="testing",
        raw_text=(
            "We suspect there's a bug that only appears if a user pauses a video, seeks "
            "backward, then pauses again before it buffers — want tests covering these "
            "action sequences."
        ),
        symptom="suspected order-dependent defect in video playback controls",
        reproducibility="not yet confirmed, tied to a specific action sequence",
        evidence_available="hypothesized sequence of user actions",
        goal_shape="coverage-increase: test specific sequences of actions/states",
        correct_framework="state_transition_testing",
    ),
    FixtureCase(
        id="ff4-b",
        kind="false_friend",
        pair_id="ff4",
        branch="testing",
        raw_text=(
            "We want test coverage for pausing videos across our three player types: "
            "HTML5, native iOS, and Chromecast, since each may behave differently."
        ),
        symptom="uncertain handling across distinct player-implementation categories",
        reproducibility="not applicable (test design, not a bug report)",
        evidence_available="known distinct player-type categories",
        goal_shape="coverage-increase: one representative test per player-type category",
        correct_framework="equivalence_partitioning",
    ),
    # --- FF-5: "nightly ETL job issue" ---
    FixtureCase(
        id="ff5-a",
        kind="false_friend",
        pair_id="ff5",
        branch="debugging",
        raw_text=(
            "The nightly ETL job silently drops rows sometimes; could be the source DB "
            "timeout, a malformed record, or the downstream write failing quietly — we "
            "don't know which."
        ),
        symptom="ETL job silently drops rows",
        reproducibility="intermittent, unconfirmed trigger",
        evidence_available="logs only, several unconfirmed candidate causes",
        goal_shape="root-cause: determine which of several plausible causes is responsible",
        correct_framework="differential_diagnosis",
    ),
    FixtureCase(
        id="ff5-b",
        kind="false_friend",
        pair_id="ff5",
        branch="debugging",
        raw_text=(
            "The nightly ETL job's dashboard shows yesterday's numbers even after a "
            "successful run, until someone manually clears the reporting cache."
        ),
        symptom="dashboard shows stale numbers after a successful run",
        reproducibility="resolves after a manual cache clear",
        evidence_available="user observation only",
        goal_shape="fix: ensure the display updates after a successful run",
        correct_framework="cache_invalidation_checklist",
    ),
    # --- DT-1: binary_search_bisection twins ---
    FixtureCase(
        id="dt1-a",
        kind="disguised_twin",
        pair_id="dt1",
        branch="debugging",
        raw_text=(
            "Our CI test suite went from 2 minutes to 12 minutes sometime in the last 40 "
            "commits; I can check out any commit to time it."
        ),
        symptom="CI runtime regressed sharply, previously fast",
        reproducibility="deterministic",
        evidence_available="ordered commit history to bisect across",
        goal_shape="root-cause: find which commit introduced the regression",
        correct_framework="binary_search_bisection",
    ),
    FixtureCase(
        id="dt1-b",
        kind="disguised_twin",
        pair_id="dt1",
        branch="debugging",
        raw_text=(
            "The mobile app's cold-start time doubled somewhere between v3.2 and v3.5; "
            "we kept every intermediate release build."
        ),
        symptom="app cold-start time regressed, previously faster",
        reproducibility="deterministic",
        evidence_available="ordered release builds to bisect across",
        goal_shape="root-cause: find which release introduced the regression",
        correct_framework="binary_search_bisection",
    ),
    # --- DT-2: differential_diagnosis twins ---
    FixtureCase(
        id="dt2-a",
        kind="disguised_twin",
        pair_id="dt2",
        branch="debugging",
        raw_text=(
            "Random customers report the app logging them out mid-session; could be "
            "token expiry, a load-balancer sticky-session issue, or a race condition on "
            "refresh — no clear pattern yet."
        ),
        symptom="users randomly logged out mid-session",
        reproducibility="intermittent, unconfirmed trigger",
        evidence_available="user reports only, several unconfirmed candidate causes",
        goal_shape="root-cause: determine which of several plausible causes is responsible",
        correct_framework="differential_diagnosis",
    ),
    FixtureCase(
        id="dt2-b",
        kind="disguised_twin",
        pair_id="dt2",
        branch="debugging",
        raw_text=(
            "Some PDF exports come out with garbled fonts; might be a font-embedding "
            "bug, a locale-specific encoding issue, or a corrupted template file — not "
            "sure which."
        ),
        symptom="PDF exports have garbled fonts",
        reproducibility="intermittent, unconfirmed trigger",
        evidence_available="sample bad exports only, several unconfirmed candidate causes",
        goal_shape="root-cause: determine which of several plausible causes is responsible",
        correct_framework="differential_diagnosis",
    ),
    # --- DT-3: cache_invalidation_checklist twins ---
    FixtureCase(
        id="dt3-a",
        kind="disguised_twin",
        pair_id="dt3",
        branch="debugging",
        raw_text=(
            "The homepage banner still shows last month's promo even after marketing "
            "updated it in the CMS, but it corrects itself overnight."
        ),
        symptom="homepage banner shows stale promo content, self-corrects overnight",
        reproducibility="intermittent, resolves after a delay",
        evidence_available="user observation only",
        goal_shape="fix: ensure the display updates promptly after a write",
        correct_framework="cache_invalidation_checklist",
    ),
    FixtureCase(
        id="dt3-b",
        kind="disguised_twin",
        pair_id="dt3",
        branch="debugging",
        raw_text=(
            "A user's shopping cart total is wrong right after they remove an item, but "
            "it's correct again if they log out and back in."
        ),
        symptom="cart total is stale after a write, resolves after re-login",
        reproducibility="resolves after a forced refresh",
        evidence_available="user observation only",
        goal_shape="fix: ensure the display updates promptly after a write",
        correct_framework="cache_invalidation_checklist",
    ),
    # --- DT-4: boundary_value_analysis twins ---
    FixtureCase(
        id="dt4-a",
        kind="disguised_twin",
        pair_id="dt4",
        branch="testing",
        raw_text=(
            "Want to verify the age-verification form correctly handles someone entering "
            "exactly 18, 17, and 19 years old."
        ),
        symptom="uncertain edge-value handling in a numeric range",
        reproducibility="not applicable (test design, not a bug report)",
        evidence_available="known min bound (18) of the input range",
        goal_shape="coverage-increase: cover exact edges of the allowed range",
        correct_framework="boundary_value_analysis",
    ),
    FixtureCase(
        id="dt4-b",
        kind="disguised_twin",
        pair_id="dt4",
        branch="testing",
        raw_text=(
            "Need to check the file-upload feature at exactly 0 bytes, exactly the 25MB "
            "limit, and 25MB-plus-one-byte."
        ),
        symptom="uncertain edge-value handling in a numeric range",
        reproducibility="not applicable (test design, not a bug report)",
        evidence_available="known min/max bounds of the input range",
        goal_shape="coverage-increase: cover exact edges of the allowed range",
        correct_framework="boundary_value_analysis",
    ),
    # --- DT-5: equivalence_partitioning twins ---
    FixtureCase(
        id="dt5-a",
        kind="disguised_twin",
        pair_id="dt5",
        branch="testing",
        raw_text=(
            "We should test the shipping-cost function against domestic addresses, "
            "international addresses, and PO boxes, since each takes a different code "
            "path."
        ),
        symptom="uncertain handling across distinct address-type categories",
        reproducibility="not applicable (test design, not a bug report)",
        evidence_available="known distinct input categories, each with its own code path",
        goal_shape="coverage-increase: one representative test per input category",
        correct_framework="equivalence_partitioning",
    ),
    FixtureCase(
        id="dt5-b",
        kind="disguised_twin",
        pair_id="dt5",
        branch="testing",
        raw_text=(
            "We should verify the login flow works for email accounts, Google SSO "
            "accounts, and SAML accounts, since they're handled by different providers."
        ),
        symptom="uncertain handling across distinct auth-provider categories",
        reproducibility="not applicable (test design, not a bug report)",
        evidence_available="known distinct input categories, each with its own code path",
        goal_shape="coverage-increase: one representative test per input category",
        correct_framework="equivalence_partitioning",
    ),
]

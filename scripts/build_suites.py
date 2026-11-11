"""Authoring source for the standard test suites. Writes suites/*.json (the frozen, versioned artifacts).

Standard suite format (JSON):
  {"suite", "version", "category", "objective", "defaults": {...}, "tasks": [{"id", "type", "prompt", ...scoring fields}]}
Bump "version" whenever a prompt, harness or scoring field changes; results record suite, version and a content hash.
"""
import hashlib, json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "suites"
OUT.mkdir(exist_ok=True)
DEFAULTS = {"temperature": 0, "seed": 1, "num_ctx": 16384, "num_predict": 1500, "think": False}


def save(name, version, category, objective, tasks, defaults=None):
    body = {"suite": name, "version": version, "category": category, "objective": objective, "defaults": {**DEFAULTS, **(defaults or {})}, "tasks": tasks}
    body["hash"] = hashlib.sha256(json.dumps(tasks, sort_keys=True).encode()).hexdigest()[:12]
    (OUT / f"{name}.json").write_text(json.dumps(body, indent=1), encoding="utf-8")
    print(name, version, len(tasks), "tasks", body["hash"])


# ---------------------------------------------------------------- code in other languages
GO_MERGE = '''package main
import ("fmt"; "os"; "reflect")
func main() {
	cases := []struct{ in, want [][]int }{
		{[][]int{{1, 3}, {2, 6}, {8, 10}, {15, 18}}, [][]int{{1, 6}, {8, 10}, {15, 18}}},
		{[][]int{{1, 4}, {4, 5}}, [][]int{{1, 5}}},
		{[][]int{}, [][]int{}},
		{[][]int{{5, 6}, {1, 2}}, [][]int{{1, 2}, {5, 6}}},
	}
	for _, c := range cases {
		got := Merge(c.in)
		if len(got) == 0 && len(c.want) == 0 { continue }
		if !reflect.DeepEqual(got, c.want) { fmt.Println("FAIL", c.in, got, c.want); os.Exit(1) }
	}
	fmt.Println("OK")
}
'''
GO_KV = '''package main
import ("fmt"; "os")
func main() {
	m := ParseKV("# c\\n a = 1 \\n\\nb=two words\\na=3\\n  # x\\nbad line\\n")
	if len(m) != 2 || m["a"] != "3" || m["b"] != "two words" { fmt.Println("FAIL", m); os.Exit(1) }
	fmt.Println("OK")
}
'''
GO_BUG_SRC = '''package main

func Avg(xs []float64) float64 {
	sum := 0.0
	for _, x := range xs {
		sum += x
	}
	return sum / float64(len(xs)+1)
}
'''
GO_BUG = '''package main
import ("fmt"; "os")
func main() {
	if Avg([]float64{2, 4, 6}) != 4 || Avg(nil) != 0 { fmt.Println("FAIL"); os.Exit(1) }
	fmt.Println("OK")
}
'''
RS_MERGE = '''mod solution;
fn v(a: &[[i32; 2]]) -> Vec<Vec<i32>> { a.iter().map(|x| x.to_vec()).collect() }
fn main() {
    assert_eq!(solution::merge(v(&[[1,3],[2,6],[8,10],[15,18]])), v(&[[1,6],[8,10],[15,18]]));
    assert_eq!(solution::merge(v(&[[1,4],[4,5]])), v(&[[1,5]]));
    assert_eq!(solution::merge(vec![]), Vec::<Vec<i32>>::new());
    assert_eq!(solution::merge(v(&[[5,6],[1,2]])), v(&[[1,2],[5,6]]));
    println!("OK");
}
'''
RS_KV = '''mod solution;
fn main() {
    let m = solution::parse_kv("# c\\n a = 1 \\n\\nb=two words\\na=3\\n  # x\\nbad line\\n");
    assert_eq!(m.len(), 2);
    assert_eq!(m.get("a").map(|s| s.as_str()), Some("3"));
    assert_eq!(m.get("b").map(|s| s.as_str()), Some("two words"));
    println!("OK");
}
'''
RS_BUG_SRC = '''pub fn avg(xs: &[f64]) -> f64 {
    let mut sum = 0.0;
    for x in xs {
        sum += x;
    }
    sum / (xs.len() as f64 + 1.0)
}
'''
RS_BUG = '''mod solution;
fn main() {
    assert_eq!(solution::avg(&[2.0, 4.0, 6.0]), 4.0);
    assert_eq!(solution::avg(&[]), 0.0);
    println!("OK");
}
'''
PS_MERGE = '''. "$PSScriptRoot\\solution.ps1"
$fail = @()
if ((@(Merge-Interval -Intervals @(@(1,3),@(2,6),@(8,10),@(15,18))) -join ',') -ne '1-6,8-10,15-18') { $fail += 'c1' }
if ((@(Merge-Interval -Intervals @(@(1,4),@(4,5))) -join ',') -ne '1-5') { $fail += 'c2' }
if ((@(Merge-Interval -Intervals @(@(5,6),@(1,2))) -join ',') -ne '1-2,5-6') { $fail += 'c3' }
if ($fail.Count) { Write-Output ('FAIL ' + ($fail -join ' ')); exit 1 }
Write-Output 'OK'
'''
PS_KV = '''. "$PSScriptRoot\\solution.ps1"
$h = ConvertFrom-KeyValue -Text "# c`n a = 1 `n`nb=two words`na=3`n  # x`nbad line`n"
if ($h.Count -ne 2 -or $h['a'] -ne '3' -or $h['b'] -ne 'two words') { Write-Output 'FAIL'; exit 1 }
Write-Output 'OK'
'''
PS_BUG_SRC = '''function Get-Average {
    param([double[]]$Numbers)
    return ($Numbers | Measure-Object -Sum).Sum / ($Numbers.Count + 1)
}
'''
PS_BUG = '''. "$PSScriptRoot\\solution.ps1"
if ((Get-Average -Numbers 2,4,6) -ne 4 -or (Get-Average -Numbers @()) -ne 0) { Write-Output 'FAIL'; exit 1 }
Write-Output 'OK'
'''
AHK_MERGE = '''#Requires AutoHotkey v2.0
#Include solution.ahk
Fmt(r) {
    s := ""
    for iv in r
        s .= (s = "" ? "" : ",") iv[1] "-" iv[2]
    return s
}
fail := ""
if (Fmt(MergeIntervals([[1,3],[2,6],[8,10],[15,18]])) != "1-6,8-10,15-18")
    fail .= "c1 "
if (Fmt(MergeIntervals([[1,4],[4,5]])) != "1-5")
    fail .= "c2 "
if (Fmt(MergeIntervals([[5,6],[1,2]])) != "1-2,5-6")
    fail .= "c3 "
if (Fmt(MergeIntervals([])) != "")
    fail .= "c4 "
FileAppend((fail = "" ? "OK" : "FAIL " fail) "`n", "*")
ExitApp
'''
AHK_KV = '''#Requires AutoHotkey v2.0
#Include solution.ahk
m := ParseKV("# c`n a = 1 `n`nb=two words`na=3`n  # x`nbad line`n")
ok := (m.Count = 2 && m["a"] = "3" && m["b"] = "two words")
FileAppend((ok ? "OK" : "FAIL") "`n", "*")
ExitApp
'''
AHK_BUG_SRC = '''Average(arr) {
    sum := 0
    for v in arr
        sum += v
    return sum / (arr.Length + 1)
}
'''
AHK_BUG = '''#Requires AutoHotkey v2.0
#Include solution.ahk
ok := (Average([2,4,6]) = 4 && Average([]) = 0)
FileAppend((ok ? "OK" : "FAIL") "`n", "*")
ExitApp
'''
ONLY = "Output only one {f} code block containing the complete file."
code_tasks = [
    ("go-merge", "go", "Write a Go file (package main, no main function, no tests) that defines `func Merge(intervals [][]int) [][]int`. It merges overlapping or touching [start, end] intervals and returns them sorted by start. An empty input returns an empty slice. " + ONLY.format(f="go"), GO_MERGE),
    ("go-kv", "go", "Write a Go file (package main, no main function) defining `func ParseKV(text string) map[string]string`. Each line is key=value. Trim spaces around keys and values. Ignore blank lines, lines whose first non-space character is #, and lines without '='. A later duplicate key overrides an earlier one. " + ONLY.format(f="go"), GO_KV),
    ("go-bugfix", "go", "This Go file should return the mean of a slice, and 0 for an empty slice, but it is wrong. Fix it. " + ONLY.format(f="go") + " Keep `package main` and do not add a main function.\n\n```go\n" + GO_BUG_SRC + "```", GO_BUG),
    ("rust-merge", "rust", "Write a Rust source file (standard library only, no fn main, no tests) that defines `pub fn merge(intervals: Vec<Vec<i32>>) -> Vec<Vec<i32>>`. It merges overlapping or touching [start, end] intervals and returns them sorted by start. An empty input returns an empty Vec. " + ONLY.format(f="rust"), RS_MERGE),
    ("rust-kv", "rust", "Write a Rust source file (standard library only, no fn main) defining `pub fn parse_kv(text: &str) -> std::collections::HashMap<String, String>`. Each line is key=value. Trim spaces around keys and values. Ignore blank lines, lines whose first non-space character is #, and lines without '='. A later duplicate key overrides an earlier one. " + ONLY.format(f="rust"), RS_KV),
    ("rust-bugfix", "rust", "This Rust file should return the mean of a slice, and 0.0 for an empty slice, but it is wrong. Fix it. " + ONLY.format(f="rust") + " Do not add a main function.\n\n```rust\n" + RS_BUG_SRC + "```", RS_BUG),
    ("ps-merge", "powershell", "Write PowerShell 7 code (function definitions only, no top-level code) defining `Merge-Interval` with a parameter `-Intervals`, an array of two-element arrays @(start,end). It merges overlapping or touching intervals, sorts by start, and outputs one string per merged interval formatted `start-end` (for example `1-6`). " + ONLY.format(f="powershell"), PS_MERGE),
    ("ps-kv", "powershell", "Write PowerShell 7 code (function definitions only, no top-level code) defining `ConvertFrom-KeyValue` with a string parameter `-Text` that returns a hashtable. Each line is key=value. Trim spaces around keys and values. Ignore blank lines, lines whose first non-space character is #, and lines without '='. A later duplicate key overrides an earlier one. " + ONLY.format(f="powershell"), PS_KV),
    ("ps-bugfix", "powershell", "This PowerShell function should return the mean of the numbers, and 0 for an empty array, but it is wrong. Fix it. " + ONLY.format(f="powershell") + " Definitions only, no top-level code.\n\n```powershell\n" + PS_BUG_SRC + "```", PS_BUG),
    ("ahk-merge", "autohotkey", "Write AutoHotkey v2 code (function definitions only, no top-level code, no #Requires line) defining `MergeIntervals(intervals)`, where intervals is an Array of two-element Arrays [start, end]. It returns an Array of merged [start, end] Arrays sorted by start, merging overlapping or touching intervals. An empty input returns an empty Array. " + ONLY.format(f="autohotkey"), AHK_MERGE),
    ("ahk-kv", "autohotkey", "Write AutoHotkey v2 code (function definitions only, no top-level code, no #Requires line) defining `ParseKV(text)` that returns a Map. Each line is key=value, lines separated by `n. Trim spaces around keys and values. Ignore blank lines, lines whose first non-space character is #, and lines without '='. A later duplicate key overrides an earlier one. " + ONLY.format(f="autohotkey"), AHK_KV),
    ("ahk-bugfix", "autohotkey", "This AutoHotkey v2 function should return the mean of the array, and 0 for an empty array, but it is wrong. Fix it. " + ONLY.format(f="autohotkey") + " Definitions only, no top-level code.\n\n```autohotkey\n" + AHK_BUG_SRC + "```", AHK_BUG),
]
save("code-languages", "1.0", "coding", "Does coding skill carry beyond Python and Terraform? Same three jobs (merge, parse, fix) in Go, Rust, PowerShell and AutoHotkey v2, executed for real.",
     [{"id": i, "type": "run_code", "lang": l, "prompt": p, "harness": h} for i, l, p, h in code_tasks])

# ---------------------------------------------------------------- summarize and categorize
LABELS = ["identity-access", "network", "endpoint", "application", "security", "cloud-infra"]
TICKETS = [
    ("T01", "User cannot sign in; the MFA prompt loops after getting a new phone.", "identity-access"),
    ("T02", "VPN connects but internal sites time out for the Boston office.", "network"),
    ("T03", "Laptop battery is swollen and the trackpad is lifting.", "endpoint"),
    ("T04", "Expense app throws a 500 error when attaching receipts.", "application"),
    ("T05", "User got an email from the 'CEO' asking for gift cards and clicked the link.", "security"),
    ("T06", "A nightly job that stops dev VMs also stopped a production VM.", "cloud-infra"),
    ("T07", "Cannot reset password; the self-service page says the account is locked.", "identity-access"),
    ("T08", "Wi-Fi drops every 20 minutes in the third-floor conference rooms.", "network"),
    ("T09", "Monitor flickers when the docking station is connected.", "endpoint"),
    ("T10", "A spreadsheet macro stopped working after the Office update.", "application"),
    ("T11", "Endpoint protection flagged an unknown executable in the Downloads folder.", "security"),
    ("T12", "The storage account firewall blocks the new build agent's IP address.", "cloud-infra"),
    ("T13", "New hire needs access to the finance share and the ERP.", "identity-access"),
    ("T14", "DNS returns the old IP for the intranet portal on some machines.", "network"),
    ("T15", "Laptop will not boot; blue screen after a driver update.", "endpoint"),
    ("T16", "CRM search returns nothing for customers added this week.", "application"),
    ("T17", "Several failed logins from another country on the admin account.", "security"),
    ("T18", "Kubernetes pods are pending because the node pool hit its quota.", "cloud-infra"),
    ("T19", "A contractor's guest account expired but they still need the project site.", "identity-access"),
    ("T20", "Packet loss between the data center and the cloud gateway during backups.", "network"),
    ("T21", "Printer driver installs fail on the new laptops.", "endpoint"),
    ("T22", "The reporting tool shows yesterday's numbers; the nightly refresh failed.", "application"),
    ("T23", "An employee lost a phone that had the corporate mail app signed in.", "security"),
    ("T24", "Terraform plan wants to destroy the production database after a provider upgrade.", "cloud-infra"),
]
DOC1 = ("Incident report INC-2291. On 14 March at 09:12 UTC the payments API began returning 429 errors. Root cause: a nightly export job introduced on 12 March ran against the primary storage account and consumed 80 percent of its request quota; a retry loop in the checkout service amplified the load. Impact: 41 minutes of degraded checkout, 3,870 failed orders and an estimated 52,000 dollars in delayed revenue; no data was lost. Detection: an alert fired at 09:19 but was routed to a retired on-call group, so a human noticed only at 09:31 from customer support reports. Mitigation: the export job was paused at 09:44 and the retry loop capped at three attempts. Contributing factors: no load test covered the export job, the quota dashboard had no alert, and the on-call rotation had not been updated after the team reorganization on 1 March. Follow-ups: move the export to a read replica by 28 March (owner Priya), add a quota alert at 60 percent by 21 March (owner Marcus), audit all alert routing by 4 April (owner Priya), and add export jobs to the quarterly load-test plan. The team decided not to roll back the checkout release because it was unrelated to the cause.")
DOC2 = ("Memo: tagging policy rollout. Effective 1 June, all new Azure resources must carry four tags: owner, cost-center, environment and data-class. Resources missing tags will be created in a non-compliant state and flagged in the weekly report; from 1 September the policy effect changes from Audit to Deny for production subscriptions only. Development and sandbox subscriptions stay on Audit until further notice. Existing resources have until 31 August to be remediated; the platform team will provide a script and two office-hour sessions per week in June. Exceptions require approval from the cloud governance board and are valid for 90 days. The expected effort is about four hours per application team. Rationale: 23 percent of last quarter's spend, roughly 410,000 dollars, could not be attributed to a team. Questions go to the cloud-governance channel. The data-class tag accepts three values: public, internal and restricted.")
DOC3 = ("Weekly platform sync. Dana opened by saying the Kubernetes upgrade to 1.31 is on track for 22 April. Luis raised that two internal apps still use a deprecated API and may break; Dana agreed to block the upgrade for those namespaces until they are fixed. Priya reported that the cost report shows a 12 percent drop in compute spend after right-sizing, saving about 18,000 dollars a month. Luis asked whether the number includes the reserved instance purchase; Priya said it does not and will rerun the analysis. Marcus proposed switching the CI runners to spot instances, estimating a 40 percent saving but noting a risk of job interruption; the group decided to pilot it on the documentation pipeline only, for four weeks, before any wider move. Dana asked about the monitoring migration; Marcus said it is blocked on a licensing quote that has not arrived, with no date. Actions: Luis to list affected apps by Friday; Priya to rerun the cost analysis next week; Marcus to set up the spot pilot; Dana to chase the licensing quote.")
SUM = "Summarize the document below in at most 120 words for an executive who has not read it. State only facts that appear in it.\n\n"
sc_tasks = [
    {"id": "categorize-tickets", "type": "labels", "labels": LABELS, "tickets": [{"id": i, "text": t, "label": l} for i, t, l in TICKETS],
     "prompt": "Classify each support ticket into exactly one label from: " + ", ".join(LABELS) + ". Return only a JSON object mapping each ticket id to its label.\n\n" + "\n".join(f"{i}: {t}" for i, t, _ in TICKETS)},
    {"id": "summarize-incident", "type": "checklist", "max_words": 120, "prompt": SUM + DOC1,
     "facts": [["429"], ["14 march", "09:12"], ["export"], ["80 percent", "80%"], ["retry"], ["41 min"], ["3,870", "3870"], ["52,000", "52k"], ["retired", "wrong group", "misrouted", "routed"], ["read replica"]],
     "forbidden": [r"(?<!no )(?<!not )data (was|were) lost", r"security (breach|incident)|attack", r"(was|were|been) rolled back"]},
    {"id": "summarize-policy", "type": "checklist", "max_words": 120, "prompt": SUM + DOC2,
     "facts": [["owner"], ["cost-center", "cost center"], ["data-class", "data class"], ["1 june"], ["1 september"], ["production"], ["31 august"], ["90 days"], ["23 percent", "23%"], ["410,000", "410k"]],
     "forbidden": [r"five tags", r"1 (july|august)", r"fines?"]},
    {"id": "summarize-meeting", "type": "checklist", "max_words": 120, "prompt": SUM + DOC3,
     "facts": [["1.31"], ["22 april"], ["deprecated"], ["12 percent", "12%"], ["18,000", "18k"], ["reserved"], ["spot"], ["documentation"], ["four weeks", "4 weeks"], ["licens"]],
     "forbidden": [r"all (ci )?(pipelines|runners)", r"monitoring migration (is |was )?(complete|done|finished)"]},
]
save("summarize-categorize", "1.0", "documents", "Condense and sort real-looking documents: accurate categorization of tickets, and executive summaries that keep the key facts, stay short and invent nothing.", sc_tasks)

# ---------------------------------------------------------------- consulting cases
STRUCT = [("structure", r"(?m)^\s*(\d+[.)]|[-*]|#{1,4})\s+\S", 5), ("assumptions", r"assum", 1), ("risks", r"\brisk", 1), ("recommendation", r"recommend|next step|propose", 1), ("hypothesis", r"hypothes", 1)]
case_tasks = [
    {"id": "case-cement-profit", "type": "case", "frameworks": [["price"], ["volume"], ["cost"], ["fixed"], ["variable"], ["energy", "fuel"], ["competit"], ["capacity"]],
     "prompt": "You are advising the CEO of a regional cement producer whose profit fell 25 percent over two years while revenue stayed flat. You know nothing about cement. Give a structured approach: your hypotheses, how you would break the problem down, the first three analyses you would run, and what you would recommend if the answer turns out to be cost-driven. Be concise."},
    {"id": "case-noshow", "type": "case", "frameworks": [["reminder", "notif"], ["overbook"], ["patient"], ["wait", "lead time", "scheduling"], ["transport"], ["cost"], ["pilot", "test"], ["data"]],
     "prompt": "A hospital outpatient clinic has a 22 percent appointment no-show rate and wants it under 10 percent. You are not a healthcare expert. Structure the problem, state assumptions, propose the interventions you would test first and how you would measure success. Be concise."},
    {"id": "case-breakeven", "type": "case", "frameworks": [["break-even", "breakeven", "payback"]], "numeric": {"pattern": "BREAKEVEN_MONTHS", "low": 20.5, "high": 22.5},
     "prompt": "A company spends 480,000 dollars a year running servers on premises. Moving to the cloud costs 300,000 dollars one-time and 310,000 dollars a year afterwards. Show your reasoning, then end with a line 'BREAKEVEN_MONTHS: <number>' giving the month in which cumulative savings cover the migration cost, and add one risk that could change the answer."},
    {"id": "case-ltv", "type": "case", "frameworks": [["ltv", "lifetime value"], ["cac"], ["churn"]], "numeric": {"pattern": "LTV_CAC", "low": 4.0, "high": 4.4},
     "prompt": "A subscription business has 2,000 customers paying 50 dollars a month, monthly churn of 3 percent and a customer acquisition cost of 400 dollars. Ignore gross margin. Compute the customer lifetime value and the LTV to CAC ratio, say whether the unit economics are healthy, and end with a line 'LTV_CAC: <number>'."},
    {"id": "case-estimate", "type": "case", "frameworks": [["population"], ["per"], ["assum"]], "numeric": {"pattern": "ESTIMATE", "low": 50, "high": 1000},
     "prompt": "Estimate how many piano tuners work in Chicago. Show a short structured estimate with your assumptions, and end with a line 'ESTIMATE: <number>'."},
    {"id": "case-market-entry", "type": "case", "frameworks": [["market"], ["compet"], ["capabilit", "advantage"], ["regulat"], ["customer"], ["entry", "enter"], ["partner"], ["question"]],
     "prompt": "A Canadian maker of industrial water filters is considering entering the Brazilian market. You know nothing about either. List the clarifying questions you would ask first, the framework you would use to structure the decision, the key assumptions you would need to test, and a go / no-go criterion. Be concise."},
]
for t in case_tasks:
    t["checks"] = [{"name": n, "re": r, "min": m} for n, r, m in STRUCT]
save("consulting-cases", "1.0", "reasoning", "Structured reasoning in unfamiliar industries: a clear breakdown, stated assumptions and risks, a recommendation, and correct numbers where the case is computable. Automatic scores are a structural proxy; depth still needs a human read.", case_tasks)

# ---------------------------------------------------------------- planted patterns
pp_tasks = [{"id": f"planted-{w}w-s{s}", "type": "planted", "weeks": w, "seed": s} for w in (104, 156) for s in (1, 2)]
save("planted-patterns", "1.0", "insight", "Does the model find non-obvious patterns in a table, and does it invent patterns that are not there? Seeded data with three planted patterns (a lagged effect, a step change, a threshold effect) and one decoy column. Score: planted patterns found, minus a penalty for claiming the decoy.", pp_tasks)

# ---------------------------------------------------------------- viable context
save("viable-context", "1.1", "context", "What context size is actually usable? At each size, three planted facts must be recalled exactly. Viable context is the largest size where all three are recalled, nothing is truncated, speed stays above the minimum and the reply arrives within the time limit. A fourth question (which code is numerically largest) is reported separately and does not gate the result. Each failure records its reason: recall, too slow, low tok/s or truncated.",
     [{"id": f"vc-{c//1024}k", "type": "viable_context", "ctx": c} for c in (8192, 16384, 32768, 65536, 131072)],
     defaults={"min_tps": 15, "max_seconds": 180})

# ---------------------------------------------------------------- images
LOGOS = [("wordmark", "a wordmark logo reading 'NORTHWIND' in bold geometric letters"), ("monogram", "a monogram logo of the letters 'LB' inside a circle"),
         ("emblem", "an emblem logo of a lighthouse with simple rays"), ("mascot", "a friendly fox mascot logo, flat shapes"), ("icon", "a minimal app icon of a leaf made from three shapes")]
SLIDES = [("hook", "Stop guessing"), ("problem", "Benchmarks lie"), ("method", "Test your own"), ("result", "Same GPU, new answer"), ("cta", "Run it yourself")]
img_tasks = [
    {"id": "logo-png", "type": "image_logo_png", "briefs": [{"id": i, "brief": b} for i, b in LOGOS], "seeds": [1, 2, 3],
     "template": "A clean flat vector logo: {brief}. Bold simple shapes, no gradients, no shadow, centered, on a solid pure green (#00FF00) background."},
    {"id": "logo-svg", "type": "image_logo_svg", "briefs": [{"id": i, "brief": b} for i, b in LOGOS],
     "template": "Write an SVG logo: {brief}. Use only basic shapes and paths, a viewBox of 0 0 512 512, no external references, no raster images, no scripts, at most 60 elements. Output only one svg code block."},
    {"id": "carousel", "type": "image_carousel", "slides": [{"id": i, "headline": h} for i, h in SLIDES], "seeds": [1], "size": [1024, 1280],
     "template": "A LinkedIn carousel slide, flat modern design, consistent navy and orange palette, large bold white headline text that reads exactly '{headline}', simple supporting graphic, plenty of margin."},
    {"id": "folder-icon", "type": "image_folder_icon", "seeds": [1],
     "template": "Turn this logo into a flat Windows folder icon: a rounded folder shape with the logo centered on its front, bold simple shapes, solid pure green (#00FF00) background."},
]
save("images", "1.0", "images", "Image generation for real jobs: transparent logo PNGs (green-key cutout, scored for spill and edge quality), SVG logos written by text models (scored for validity and cleanliness), a five-slide LinkedIn carousel (headline legibility read back by a vision model), and a folder icon derived from a generated logo (checked at small sizes). ICO conversion is out of scope.", img_tasks,
     defaults={"steps": {"z-image": 8, "flux2-klein": 4, "sdxl": 25}})

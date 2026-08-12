#!/usr/bin/env python3
"""Build the Three.js Game Specification Forge.

Reads workflow.json and renders workflow.html: a local-first, static specification
wizard that exports a canonical game spec, dependency preflight, and a bounded
Gauntlet Loop handoff prompt. No backend and no user answers leave the browser.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "workflow.json"
OUT = ROOT / "workflow.html"


def main():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    validate(payload)
    steps = payload.get("steps", [])
    fields = sum(len(step.get("fields", [])) for step in steps)
    print(f"Loaded {len(steps)} steps and {fields} specification fields")
    html = render(json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(html) / 1024:.0f} KB)")


def validate(payload: dict) -> None:
    """Reject drift in the declarative workflow before publishing HTML."""
    steps = payload.get("steps", [])
    if not steps:
        raise ValueError("workflow.json must contain at least one step")
    step_ids = [step.get("id") for step in steps]
    if len(step_ids) != len(set(step_ids)) or any(not value for value in step_ids):
        raise ValueError("workflow step IDs must be present and unique")

    fields = [field for step in steps for field in step.get("fields", [])]
    field_ids = [field.get("id") for field in fields]
    if len(field_ids) != len(set(field_ids)) or any(not value for value in field_ids):
        raise ValueError("workflow field IDs must be present and globally unique")
    for field in fields:
        if not field.get("label") or not field.get("type"):
            raise ValueError(f"field {field.get('id')} needs label and type")
        if field["type"] in {"choice", "multi"} and not field.get("options"):
            raise ValueError(f"field {field['id']} needs options")
        if field["type"] == "number" and "default" in field:
            if "min" in field and field["default"] < field["min"]:
                raise ValueError(f"field {field['id']} default is below min")
            if "max" in field and field["default"] > field["max"]:
                raise ValueError(f"field {field['id']} default is above max")

    known_fields = set(field_ids)
    for field in fields:
        condition = field.get("requiredWhen")
        conditions = condition.get("any", []) if condition else []
        if condition and not conditions:
            conditions = [condition]
        for item in conditions:
            if item.get("field") not in known_fields:
                raise ValueError(f"field {field['id']} has requiredWhen on unknown field {item.get('field')}")
    for index, rule in enumerate(payload.get("resourceRules", [])):
        if not rule.get("always") and rule.get("field") not in known_fields:
            raise ValueError(f"resource rule {index} references unknown field {rule.get('field')}")
        if not rule.get("resources") and not rule.get("skills"):
            raise ValueError(f"resource rule {index} routes nothing")


def render(data_json: str) -> str:
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Incremental Three.js game specification workflow with dependency routing and a budget-governed Gauntlet Loop handoff.">
<title>Three.js Game Specification Forge</title>
<style>
:root {
  --bg:#080b12; --panel:#101621; --panel2:#151d2b; --panel3:#0c111b;
  --line:#223047; --text:#edf4fb; --muted:#93a3b8; --green:#68e0b0;
  --blue:#50b7f5; --amber:#f6c76c; --red:#ff7d8f; --violet:#a99bff;
  --shadow:0 20px 60px rgba(0,0,0,.28); --radius:16px;
}
*{box-sizing:border-box} html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font-family:"Segoe UI",Inter,system-ui,-apple-system,sans-serif;line-height:1.5}
button,input,textarea{font:inherit} button{cursor:pointer}
a{color:var(--blue)}
.app{min-height:100vh}
.topbar{height:58px;position:sticky;top:0;z-index:50;background:rgba(8,11,18,.92);backdrop-filter:blur(16px);border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 20px;gap:16px}
.brand{font-weight:850;letter-spacing:-.02em;white-space:nowrap}.brand .mark{color:var(--green)}
.topnav{display:flex;gap:14px;font-size:.82rem}.topnav a{text-decoration:none;color:var(--muted)}.topnav a:hover{color:var(--text)}
.top-actions{margin-left:auto;display:flex;gap:8px;align-items:center}
.privacy{font-size:.73rem;color:var(--muted);white-space:nowrap}.privacy b{color:var(--green)}
.btn{border:1px solid var(--line);background:var(--panel2);color:var(--text);padding:9px 13px;border-radius:10px;font-weight:700;font-size:.82rem;transition:.15s}
.btn:hover{border-color:#3d567a;transform:translateY(-1px)}.btn.primary{background:var(--green);color:#061b13;border-color:var(--green)}
.btn:disabled{cursor:not-allowed;opacity:.42;transform:none;border-color:var(--line)}
.btn.danger{color:var(--red)}.btn.small{padding:7px 10px;font-size:.75rem}
.layout{max-width:1540px;margin:auto;display:grid;grid-template-columns:265px minmax(0,840px) 320px;gap:22px;padding:24px 20px 80px}
.sidebar,.inspector{position:sticky;top:82px;align-self:start;max-height:calc(100vh - 104px);overflow:auto;scrollbar-width:thin}
.project-intro{padding:3px 4px 17px}.project-intro h1{font-size:1.28rem;margin:0;letter-spacing:-.02em}.project-intro p{font-size:.8rem;color:var(--muted);margin:7px 0 0}
.progress-track{height:6px;background:var(--panel2);border-radius:999px;overflow:hidden;margin:12px 0 7px}.progress-fill{height:100%;background:linear-gradient(90deg,var(--green),var(--blue));transition:width .2s}
.progress-label{display:flex;justify-content:space-between;font-size:.72rem;color:var(--muted)}
.step-list{display:grid;gap:5px;margin-top:13px}.step-tab{border:1px solid transparent;background:transparent;color:var(--muted);border-radius:11px;text-align:left;padding:10px 11px;display:grid;grid-template-columns:27px 1fr auto;gap:8px;align-items:center}
.step-tab:hover{background:var(--panel);color:var(--text)}.step-tab.active{background:var(--panel2);border-color:var(--line);color:var(--text)}
.step-num{width:25px;height:25px;border-radius:8px;background:var(--panel3);display:grid;place-items:center;font-size:.72rem;font-weight:800}.step-tab.done .step-num{background:#10352a;color:var(--green)}
.step-title{font-size:.78rem;font-weight:700}.step-state{font-size:.68rem}.step-tab.done .step-state{color:var(--green)}.step-tab.incomplete .step-state{color:var(--amber)}
.local-tools{border-top:1px solid var(--line);margin-top:16px;padding-top:14px;display:flex;gap:7px;flex-wrap:wrap}
.main{min-width:0}.hero{border:1px solid var(--line);background:linear-gradient(145deg,#131c2b,#0f1723);border-radius:20px;padding:26px 28px;margin-bottom:16px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.hero:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;right:-100px;top:-140px;background:radial-gradient(circle,rgba(80,183,245,.16),transparent 68%)}
.eyebrow{font-size:.72rem;color:var(--green);font-weight:850;text-transform:uppercase;letter-spacing:.09em}.hero h2{font-size:1.8rem;line-height:1.1;margin:8px 0 9px;letter-spacing:-.035em}.hero p{color:var(--muted);margin:0;max-width:680px;font-size:.92rem}
.form-card{border:1px solid var(--line);background:var(--panel);border-radius:20px;padding:12px 26px 24px}
.suggestion-bar{display:flex;align-items:center;justify-content:space-between;gap:14px;margin:12px 0 2px;padding:13px 14px;border:1px solid #3a3565;background:linear-gradient(135deg,#17152b,#111927);border-radius:13px}.suggestion-copy b{display:block;font-size:.82rem;color:#d8d1ff}.suggestion-copy span{display:block;margin-top:2px;color:var(--muted);font-size:.72rem}.btn.lucky{flex:0 0 auto;border-color:#5d52a0;background:#29224d;color:#e7e2ff}.btn.lucky:hover{border-color:var(--violet)}
.field{padding:20px 0;border-bottom:1px solid var(--line)}.field:last-child{border-bottom:0}.field-head{display:flex;gap:8px;align-items:baseline;margin-bottom:8px}.field label{font-size:.9rem;font-weight:800}.req{color:var(--amber);font-size:.72rem}.optional{font-size:.7rem;color:var(--muted)}
.help{font-size:.76rem;color:var(--muted);margin:-2px 0 9px}
.text-input,.text-area,.number-input{width:100%;border:1px solid var(--line);background:var(--panel3);color:var(--text);border-radius:11px;padding:11px 12px;outline:none}.text-area{min-height:92px;resize:vertical}.text-area.lines{min-height:116px;font-family:"Cascadia Code",Consolas,monospace;font-size:.82rem}.number-input{max-width:220px}
.text-input:focus,.text-area:focus,.number-input:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(80,183,245,.1)}.field.error .text-input,.field.error .text-area,.field.error .number-input,.field.error .choices{border-color:var(--red)}
.error-msg{display:none;color:var(--red);font-size:.72rem;margin-top:7px}.field.error .error-msg{display:block}
.choices{display:flex;gap:8px;flex-wrap:wrap;border:1px solid transparent;border-radius:11px}.choice{position:relative}.choice input{position:absolute;opacity:0}.choice span{display:block;border:1px solid var(--line);background:var(--panel3);color:var(--muted);padding:8px 11px;border-radius:9px;font-size:.78rem;transition:.12s}.choice input:checked+span{background:#11362c;border-color:#2a8069;color:var(--green);font-weight:750}.choice input:focus-visible+span{outline:2px solid var(--blue);outline-offset:2px}.choice span:hover{border-color:#3c5475;color:var(--text)}
.form-nav{display:flex;justify-content:space-between;align-items:center;margin-top:16px;gap:10px}.save-state{font-size:.74rem;color:var(--muted)}.save-state.saved{color:var(--green)}
.inspector-section{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:15px;margin-bottom:12px}.inspector h3{font-size:.86rem;margin:0 0 10px}.status-ring{display:flex;align-items:center;gap:12px}.ring{--p:0;width:54px;height:54px;border-radius:50%;background:conic-gradient(var(--green) calc(var(--p)*1%),var(--panel2) 0);display:grid;place-items:center}.ring:after{content:"";width:42px;height:42px;border-radius:50%;background:var(--panel);position:absolute}.ring b{position:relative;z-index:1;font-size:.72rem}.status-copy b{display:block;font-size:.83rem}.status-copy span{font-size:.72rem;color:var(--muted)}
.missing-list{margin:0;padding:0;list-style:none;display:grid;gap:6px}.missing-list li{font-size:.72rem;color:var(--muted);display:flex;gap:7px}.missing-list li:before{content:"•";color:var(--amber)}
.route-list{display:grid;gap:7px}.route{background:var(--panel3);border:1px solid var(--line);border-radius:9px;padding:8px 9px}.route b{display:block;font-size:.75rem}.route span{display:block;color:var(--muted);font-size:.68rem;margin-top:2px}.route a{text-decoration:none;color:var(--text)}
.skill-tags{display:flex;gap:5px;flex-wrap:wrap}.skill-tag{font-family:"Cascadia Code",Consolas,monospace;font-size:.65rem;color:var(--violet);border:1px solid #3a3565;background:#17152b;padding:4px 6px;border-radius:6px}
.final-panel{border:1px solid #2a8069;background:linear-gradient(145deg,#10231f,#0e1721);border-radius:20px;padding:22px 24px;margin-top:16px}.final-panel.locked{border-color:var(--line);opacity:.82}.final-panel h3{margin:0;font-size:1.15rem}.final-panel p{color:var(--muted);font-size:.82rem}.export-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:14px}.export-card{border:1px solid var(--line);background:var(--panel3);border-radius:11px;padding:12px}.export-card b{font-size:.8rem;display:block}.export-card p{font-size:.7rem;margin:4px 0 10px}.export-card .btn{width:100%}
.prompt-preview{margin-top:14px;border:1px solid var(--line);background:#080c13;border-radius:12px;padding:14px;max-height:260px;overflow:auto;white-space:pre-wrap;font-family:"Cascadia Code",Consolas,monospace;font-size:.69rem;color:#c8d5e4}
.toast{position:fixed;right:22px;bottom:22px;background:#173a31;color:var(--green);border:1px solid #2b806a;padding:10px 14px;border-radius:10px;font-size:.8rem;font-weight:750;opacity:0;transform:translateY(10px);pointer-events:none;transition:.2s;z-index:100}.toast.show{opacity:1;transform:none}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.7);display:none;place-items:center;z-index:90;padding:20px}.modal.open{display:grid}.modal-card{max-width:560px;width:100%;background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px}.modal-card h3{margin:0}.modal-card p{color:var(--muted);font-size:.83rem}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}
@media(max-width:1160px){.layout{grid-template-columns:230px minmax(0,1fr)}.inspector{display:none}}
@media(max-width:780px){.privacy{display:none}.layout{display:block;padding:14px 12px 70px}.sidebar{position:static;max-height:none}.step-list{display:flex;overflow:auto;padding-bottom:8px}.step-tab{min-width:155px}.project-intro{padding-top:10px}.main{margin-top:12px}.hero,.form-card{padding-left:18px;padding-right:18px}.suggestion-bar{align-items:flex-start;flex-direction:column}.btn.lucky{width:100%}.export-grid{grid-template-columns:1fr}.topbar{height:auto;min-height:58px;padding:8px 12px;flex-wrap:wrap}.brand{font-size:.88rem}.top-actions{order:2;width:100%;margin-left:0;justify-content:flex-start;gap:6px}.topnav{order:3;width:100%;overflow-x:auto;white-space:nowrap;padding:2px 0}}
</style>
</head>
<body>
<div class="app">
  <header class="topbar">
    <div class="brand"><span class="mark">◆</span> Spec Forge</div>
    <nav class="topnav"><a href="index.html">Catalog</a><a href="assets.html">Assets</a><a href="cheatsheet.html">Skill cheat sheet</a></nav>
    <div class="top-actions"><span class="privacy"><b>Local-only:</b> answers stay in this browser</span><button class="btn small" id="importBtn">Import</button><button class="btn primary small" id="downloadDraftBtn">Save draft</button></div>
  </header>
  <div class="layout">
    <aside class="sidebar">
      <div class="project-intro"><h1 id="appTitle"></h1><p id="appSubtitle"></p><div class="progress-track"><div class="progress-fill" id="progressFill"></div></div><div class="progress-label"><span id="progressText"></span><span id="versionText"></span></div></div>
      <div class="step-list" id="stepList"></div>
      <div class="local-tools"><button class="btn small" id="startOverBtn">Start over</button><button class="btn small" id="copyDraftBtn">Copy draft JSON</button></div>
    </aside>
    <main class="main">
      <section class="hero"><div class="eyebrow" id="stepEyebrow"></div><h2 id="stepTitle"></h2><p id="stepDescription"></p></section>
      <section class="form-card"><div class="suggestion-bar"><div class="suggestion-copy"><b>Need a credible starting point?</b><span id="luckyHint">Uses decisions from earlier stages and fills only unanswered fields.</span></div><button class="btn lucky" id="luckyBtn" type="button">✨ I'm Feeling Lucky</button></div><div id="formFields"></div><div class="form-nav"><button class="btn" id="backBtn">← Back</button><span class="save-state" id="saveState">Local autosave ready</span><button class="btn primary" id="nextBtn">Continue →</button></div></section>
      <section class="final-panel locked" id="finalPanel">
        <h3 id="finalTitle">Handoff exports unlock when the required decisions are complete.</h3>
        <p id="finalDescription">You can export a draft at any time. A ready packet contains the canonical game specification, routed dependencies and skills, budget policy, and the agent directive.</p>
        <div class="export-grid">
          <div class="export-card"><b>Canonical game specification</b><p>Human-readable product and technical decisions plus resource routing.</p><button class="btn" data-export="spec">Download GAME_SPEC.md</button></div>
          <div class="export-card"><b>Self-contained Gauntlet handoff</b><p>Short directive plus the complete attached specification.</p><button class="btn" data-export="prompt">Copy handoff prompt</button></div>
          <div class="export-card"><b>Implementation packet</b><p>Specification, dependency preflight contract, budget governor, and report format.</p><button class="btn" data-export="packet">Download implementation packet</button></div>
          <div class="export-card"><b>Machine-readable canon</b><p>Answers, routed resources, skill list, completion state, and schema version.</p><button class="btn" data-export="json">Download GAME_SPEC.json</button></div>
        </div>
        <div class="prompt-preview" id="promptPreview"></div>
      </section>
    </main>
    <aside class="inspector">
      <div class="inspector-section"><h3>Specification status</h3><div class="status-ring"><div class="ring" id="ring"><b id="ringText">0%</b></div><div class="status-copy"><b id="statusTitle">Draft</b><span id="statusCopy"></span></div></div></div>
      <div class="inspector-section"><h3>Missing in this step</h3><ul class="missing-list" id="missingList"></ul></div>
      <div class="inspector-section"><h3>Routed resources</h3><div class="route-list" id="routeList"></div></div>
      <div class="inspector-section"><h3>Agent skills</h3><div class="skill-tags" id="skillTags"></div></div>
    </aside>
  </div>
</div>
<div class="toast" id="toast"></div>
<div class="modal" id="resetModal"><div class="modal-card"><h3>Start over?</h3><p>This removes the locally saved answers for this workflow. Download a draft first if you may need them.</p><div class="modal-actions"><button class="btn" id="cancelReset">Cancel</button><button class="btn danger" id="confirmReset">Delete local draft</button></div></div></div>
<input id="importFile" type="file" accept="application/json,.json" hidden>
<script id="workflow-data" type="application/json">__DATA__</script>
<script>
'use strict';
const WORKFLOW = JSON.parse(document.getElementById('workflow-data').textContent);
const STEPS = WORKFLOW.steps;
const ALL_FIELDS = STEPS.flatMap(s => s.fields.map(f => ({...f, stepId:s.id, stepTitle:s.title})));
const STORAGE_KEY = WORKFLOW.meta.storageKey;
const DEFAULT_STATE = {answers:{}, currentStep:0, startedAt:new Date().toISOString(), updatedAt:new Date().toISOString()};
let state = loadState();
let saveTimer;
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

function loadState(){
  try{
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if(stored && typeof stored==='object'&&!Array.isArray(stored)){
      const currentStep=Number.isInteger(stored.currentStep)?Math.max(0,Math.min(STEPS.length-1,stored.currentStep)):0;
      return {...DEFAULT_STATE,startedAt:typeof stored.startedAt==='string'?stored.startedAt:DEFAULT_STATE.startedAt,updatedAt:typeof stored.updatedAt==='string'?stored.updatedAt:DEFAULT_STATE.updatedAt,currentStep,answers:normalizeAnswers(stored.answers)};
    }
  }catch(e){console.warn('Could not load local draft',e)}
  return structuredClone(DEFAULT_STATE);
}
function saveState(){
  state.updatedAt=new Date().toISOString();
  try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state))}catch(e){$('#saveState').textContent='Autosave unavailable — download a draft';$('#saveState').classList.remove('saved');return false}
  $('#saveState').textContent='Saved locally'; $('#saveState').classList.add('saved');
  clearTimeout(saveTimer); saveTimer=setTimeout(()=>{$('#saveState').textContent='All changes autosave locally'},1200);
  return true;
}
function normalizeAnswers(source){const clean={};if(!source||typeof source!=='object'||Array.isArray(source))return clean;ALL_FIELDS.forEach(f=>{if(Object.prototype.hasOwnProperty.call(source,f.id))clean[f.id]=source[f.id]});return clean}
function valuePresent(v){return Array.isArray(v)?v.length>0:(v!==undefined&&v!==null&&String(v).trim()!=='')}
function fieldIsRequired(f){
  if(f.required)return true;
  const condition=f.requiredWhen;if(!condition)return false;
  const conditions=condition.any||[condition];
  return conditions.some(item=>{const source=state.answers[item.field];const values=Array.isArray(source)?source:[source];return (item.containsAny||[]).some(needle=>values.some(value=>String(value||'').includes(needle))) });
}
function requiredFields(){return ALL_FIELDS.filter(fieldIsRequired)}
function numberOnStep(value,min,step){if(!step)return true;const base=min??0;return Math.abs(((value-base)/step)-Math.round((value-base)/step))<1e-8}
function fieldValueValid(f,value){
  if(!valuePresent(value))return !fieldIsRequired(f);
  if(f.type==='number'){return typeof value==='number'&&Number.isFinite(value)&&(f.min===undefined||value>=f.min)&&(f.max===undefined||value<=f.max)&&numberOnStep(value,f.min,f.step)}
  if(f.type==='choice')return typeof value==='string'&&f.options.includes(value);
  if(f.type==='multi')return Array.isArray(value)&&value.length>0&&value.every(item=>f.options.includes(item));
  return typeof value==='string';
}
function fieldHasIssue(f){return !fieldValueValid(f,state.answers[f.id])}
function allIssues(){return ALL_FIELDS.filter(fieldHasIssue)}
function missingRequired(){return requiredFields().filter(fieldHasIssue)}
function stepMissing(step){return step.fields.filter(fieldHasIssue)}
function completion(){const req=requiredFields();return req.length?Math.round(req.filter(f=>!fieldHasIssue(f)).length/req.length*100):100}
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function slug(s){return (s||'threejs-game').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,60)||'threejs-game'}
function lines(v){return String(v||'').split(/\r?\n/).map(s=>s.trim()).filter(Boolean)}
function asText(v){return Array.isArray(v)?v.join(', '):String(v??'')}
function showToast(msg){const t=$('#toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),1800)}

function init(){
  $('#appTitle').textContent=WORKFLOW.meta.title;
  $('#appSubtitle').textContent=WORKFLOW.meta.subtitle;
  $('#versionText').textContent='v'+WORKFLOW.meta.version;
  bindGlobal(); applyDefaults(); render();
}
function applyDefaults(){
  ALL_FIELDS.forEach(f=>{if(state.answers[f.id]===undefined&&f.default!==undefined)state.answers[f.id]=f.default});
}
function bindGlobal(){
  $('#backBtn').onclick=()=>goTo(state.currentStep-1);
  $('#nextBtn').onclick=()=>{if(!validateCurrent())return;if(state.currentStep===STEPS.length-1)$('#finalPanel').scrollIntoView({behavior:'smooth',block:'start'});else goTo(state.currentStep+1)};
  $('#startOverBtn').onclick=()=>$('#resetModal').classList.add('open');
  $('#cancelReset').onclick=()=>$('#resetModal').classList.remove('open');
  $('#confirmReset').onclick=()=>{try{localStorage.removeItem(STORAGE_KEY)}catch(e){}state=structuredClone(DEFAULT_STATE);applyDefaults();$('#resetModal').classList.remove('open');render();showToast('Local draft cleared')};
  $('#downloadDraftBtn').onclick=()=>download(`${slug(state.answers.title)}-spec-draft.json`,JSON.stringify(buildJsonExport(),null,2),'application/json');
  $('#copyDraftBtn').onclick=()=>copyText(JSON.stringify(buildJsonExport(),null,2),'Draft JSON copied');
  $('#importBtn').onclick=()=>$('#importFile').click();
  $('#importFile').onchange=importDraft;
  $('#luckyBtn').onclick=applyLuckySuggestions;
  $$('[data-export]').forEach(b=>b.onclick=()=>handleExport(b.dataset.export));
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();saveState();showToast('Draft saved locally')}});
}
function goTo(i){state.currentStep=Math.max(0,Math.min(STEPS.length-1,i));saveState();render();window.scrollTo({top:0,behavior:'smooth'})}
function validateCurrent(){
  const missing=stepMissing(STEPS[state.currentStep]);
  $$('.field').forEach(el=>el.classList.remove('error'));
  missing.forEach(f=>document.querySelector(`[data-field="${CSS.escape(f.id)}"]`)?.classList.add('error'));
  if(missing.length){showToast(`${missing.length} decision${missing.length===1?'':'s'} need attention`);document.querySelector('.field.error')?.scrollIntoView({behavior:'smooth',block:'center'});return false}
  return true;
}
function render(){renderSteps();renderForm();renderInspector();renderFinal()}
function renderSteps(){
  const pct=completion();$('#progressFill').style.width=pct+'%';$('#progressText').textContent=`${pct}% required decisions complete`;
  $('#stepList').innerHTML=STEPS.map((s,i)=>{const miss=stepMissing(s).length;const active=i===state.currentStep;const done=miss===0;return `<button class="step-tab ${active?'active':''} ${done?'done':'incomplete'}" data-step="${i}"><span class="step-num">${done?'✓':i+1}</span><span class="step-title">${esc(s.title)}</span><span class="step-state">${done?'done':miss}</span></button>`}).join('');
  $$('.step-tab').forEach(b=>b.onclick=()=>goTo(Number(b.dataset.step)));
}
function renderForm(){
  const step=STEPS[state.currentStep];$('#stepEyebrow').textContent=step.eyebrow;$('#stepTitle').textContent=step.title;$('#stepDescription').textContent=step.description;
  $('#formFields').innerHTML=step.fields.map(renderField).join(''); bindFields(step);
  const open=Object.keys(buildLuckySuggestions(step)).length;$('#luckyBtn').disabled=open===0;$('#luckyHint').textContent=open?`Uses decisions from earlier stages and can fill ${open} unanswered field${open===1?'':'s'}. Existing answers stay untouched.`:'No contextual suggestions remain for this stage. Clear a field if you want a new suggestion for it.';
  $('#backBtn').disabled=state.currentStep===0;
  $('#nextBtn').textContent=state.currentStep===STEPS.length-1?'Review handoff ↓':'Continue →';
}
function renderField(f){
  const value=state.answers[f.id];const req=fieldIsRequired(f)?'<span class="req">Required</span>':'<span class="optional">Optional</span>';
  let control='';
  if(['text','number'].includes(f.type)){
    const cls=f.type==='number'?'number-input':'text-input';
    control=`<input class="${cls}" id="${esc(f.id)}" type="${f.type}" value="${esc(value??'')}" placeholder="${esc(f.placeholder||'')}" ${f.min!==undefined?`min="${f.min}"`:''} ${f.max!==undefined?`max="${f.max}"`:''} ${f.step!==undefined?`step="${f.step}"`:''}>`;
  }else if(['textarea','lines'].includes(f.type)){
    control=`<textarea class="text-area ${f.type==='lines'?'lines':''}" id="${esc(f.id)}" placeholder="${esc(f.placeholder||'')}">${esc(value??'')}</textarea>`;
  }else if(f.type==='choice'){
    control=`<div class="choices">${f.options.map((o,i)=>`<label class="choice"><input type="radio" name="${esc(f.id)}" value="${esc(o)}" ${value===o?'checked':''}><span>${esc(o)}</span></label>`).join('')}</div>`;
  }else if(f.type==='multi'){
    const selected=Array.isArray(value)?value:[];
    control=`<div class="choices">${f.options.map(o=>`<label class="choice"><input type="checkbox" name="${esc(f.id)}" value="${esc(o)}" ${selected.includes(o)?'checked':''}><span>${esc(o)}</span></label>`).join('')}</div>`;
  }
  return `<div class="field" data-field="${esc(f.id)}"><div class="field-head"><label for="${esc(f.id)}">${esc(f.label)}</label>${req}</div>${f.help?`<div class="help">${esc(f.help)}</div>`:''}${control}<div class="error-msg">Provide an allowed value before continuing.</div></div>`;
}
function bindFields(step){
  step.fields.forEach(f=>{
    if(['text','number','textarea','lines'].includes(f.type)){
      const el=document.getElementById(f.id);el.addEventListener('input',()=>{state.answers[f.id]=f.type==='number'?(el.value===''?'':Number(el.value)):el.value;fieldChanged(f.id)});
    }else{
      $$(`[name="${CSS.escape(f.id)}"]`).forEach(el=>el.addEventListener('change',()=>{
        if(f.type==='choice')state.answers[f.id]=$(`[name="${CSS.escape(f.id)}"]:checked`)?.value||'';
        else state.answers[f.id]=$$(`[name="${CSS.escape(f.id)}"]:checked`).map(x=>x.value);
        fieldChanged(f.id);renderForm();
      }));
    }
  });
}
function fieldChanged(id){document.querySelector(`[data-field="${CSS.escape(id)}"]`)?.classList.remove('error');saveState();renderSteps();renderInspector();renderFinal()}

const LUCKY_STARTERS=[
  {title:'Neon Salvage',pitch:'Lead a salvage crew through a collapsing neon megastructure, choosing what to rescue before the route seals behind you.',genre:'Isometric extraction action game',audience:'Players who enjoy readable action, short tactical runs, and meaningful risk/reward choices',platforms:['Desktop web'],sessionLength:'5–15 minutes'},
  {title:'Signal Garden',pitch:'Restore a silent orbital garden by routing light, water, and forgotten machine signals through compact spatial puzzles.',genre:'Atmospheric puzzle exploration game',audience:'Players who enjoy contemplative discovery, elegant systems, and low-pressure mastery',platforms:['Desktop web','Tablet web'],sessionLength:'15–30 minutes'},
  {title:'Skybreak Relay',pitch:'Thread a courier skiff through storm-broken sky lanes while chaining risky shortcuts to keep a failing relay alive.',genre:'Arcade flight racing game',audience:'Players who enjoy immediate controls, score chasing, and replayable route mastery',platforms:['Desktop web','Gamepad'],sessionLength:'2–5 minutes'}
];
function luckyContext(){
  const a=state.answers,seed=String(state.startedAt||'').split('').reduce((sum,ch)=>sum+ch.charCodeAt(0),0),starter=LUCKY_STARTERS[seed%LUCKY_STARTERS.length];
  const title=asText(a.title)||starter.title,genre=asText(a.genre)||starter.genre,pitch=asText(a.pitch)||starter.pitch,audience=asText(a.audience)||starter.audience,lower=`${genre} ${pitch}`.toLowerCase();
  const platforms=Array.isArray(a.platforms)&&a.platforms.length?a.platforms:starter.platforms,modes=Array.isArray(a.modes)?a.modes:[],chosenSystems=Array.isArray(a.systems)?a.systems:[];
  return {a,starter,title,genre,pitch,audience,lower,platforms,modes,mobile:platforms.some(x=>['Mobile web','Tablet web'].includes(x)),flight:/flight|racing|vehicle|driving|skiff|ship/.test(lower),puzzle:/puzzle|strategy|builder|management|card/.test(lower),action:/action|combat|shooter|fighter|survival|extraction|rogue/.test(lower),firstPerson:/first.person|fps/.test(lower),sideOn:/platformer|side.scroll/.test(lower),online:modes.some(x=>x.startsWith('Online'))||chosenSystems.includes('Online multiplayer')||a.networking==='Authoritative online multiplayer'};
}
function buildLuckySuggestions(step){
  const c=luckyContext(),a=c.a,name=c.title,genre=c.genre,pitch=c.pitch,actionLoop=c.flight?'scan the route → commit to a line → evade hazards → collect salvage → bank score → choose a riskier shortcut':c.puzzle?'inspect the space → form a hypothesis → manipulate one system → observe feedback → unlock a new layer':'read the threat → choose position → act → collect the reward → recover → re-enter at higher pressure';
  const perspective=c.flight?'Vehicle chase':c.firstPerson?'First person':c.sideOn?'Side-on':c.puzzle?'Top-down / isometric':'Third-person follow';
  const primaryVerbs=c.flight?'Steer, boost, brake, drift, scan, collect, and choose routes. Mastery comes from preserving speed while reading hazards early.':c.puzzle?'Move, inspect, rotate, connect, activate, and rewind. Each verb must produce immediate visual and audio feedback.':'Move, aim, dash, strike, evade, interact, and collect. Timing and positioning should matter more than stat inflation.';
  const inferredSystems=c.puzzle?['Quests / objectives','Persistence / saves','Replay / deterministic sim']:[...(c.action?['Combat','Enemy AI']:[]),...(c.flight?['Physics-heavy movement']:[]),'Quests / objectives','Persistence / saves','Replay / deterministic sim'];
  if(c.online&&!inferredSystems.includes('Online multiplayer'))inferredSystems.push('Online multiplayer');
  const systems=Array.isArray(a.systems)&&a.systems.length?[...a.systems]:inferredSystems;
  const suggested={};
  if(step.id==='vision'){
    const s=c.starter,title=asText(a.title)||s.title,genre=asText(a.genre)||s.genre,pitch=asText(a.pitch)||s.pitch,audience=asText(a.audience)||s.audience,existing=a.repoMode==='Implement in an existing repository'||(valuePresent(a.repoTarget)&&a.repoMode!=='Create a new repository');
    const baseline=existing?'Inspect the existing code, assets, documentation, build/runtime path, fixed integrations, unresolved constraints, and prior decisions before proposing architecture or changing files.':'None — greenfield project. Preserve the static-hosting constraint, keep the first slice reversible, and record every added dependency.';
    Object.assign(suggested,{repoMode:existing?'Implement in an existing repository':'Create a new repository',repoTarget:existing?asText(a.repoTarget):slug(title),baselineEvidence:baseline,title,pitch,genre,audience,platforms:Array.isArray(a.platforms)&&a.platforms.length?a.platforms:s.platforms,sessionLength:asText(a.sessionLength)||s.sessionLength,deliveryScope:`A polished vertical slice of ${title}: title screen, in-context onboarding, one complete ${genre.toLowerCase()} run, fail/retry, success recap, production build, and browser verification.`,nonGoals:'No accounts, monetization, live-service backend, large campaign, or speculative content beyond the first complete slice.'});
  }else if(step.id==='bar')Object.assign(suggested,{referenceUrls:'https://threejs.org/examples/\nhttps://jawnzilla.github.io/threejs-game-resources/assets.html',visualBar:`At fixed hero views, ${name} must have a coherent silhouette, lighting hierarchy, material language, and effect readability that hold up beside its selected references.`,gameplayBar:`A fresh player can understand ${pitch.charAt(0).toLowerCase()+pitch.slice(1)} They can complete, fail, and retry one representative run without instructions outside the game.`,technicalBar:`The production build completes the primary ${genre.toLowerCase()} journey without console errors, broken inputs, missing assets, or visible frame-time spikes on the declared target device.`,comparisonMethod:['Side-by-side video','Playable journey','Automated tests','Frame-time capture'],barSentence:`${name}'s first five minutes must communicate its promise and win a side-by-side readability comparison while the deployed build passes the primary journey and performance gates.`,referenceBoundary:'Match quality, not protected content'});
  else if(step.id==='experience')Object.assign(suggested,{perspective,primaryVerbs,targetFeeling:c.flight?'Fast, precise, exposed, and exhilarating once the route is mastered':c.puzzle?'Curious, calm, clever, and rewarded by visible systemic understanding':'Responsive, readable, dangerous, and empowering through mastery',desktopControls:c.flight?'WASD or left stick steers; mouse/right stick looks; Space/trigger boosts; Shift/brake controls drift; all actions are remappable with gamepad parity.':c.puzzle?'WASD/arrow keys move; mouse selects and manipulates; Space confirms; R rewinds the last safe action; keyboard-only menus are supported.':'WASD/left stick moves; mouse/right stick aims; primary action attacks; Space/dedicated face button evades; E/interact is remappable with gamepad parity.',onboarding:`First show the objective and one safe verb, then let the player perform it, introduce one consequence, award a visible success, and end the first 90 seconds with a meaningful ${genre.toLowerCase()} decision.`,accessibility:['Remappable controls','Keyboard-only menus','Color-independent cues','Subtitles','Reduced motion','Screen-shake slider','Text scaling'],...(c.mobile?{touchControls:'Use a left movement stick with a generous dead zone, right-side contextual action buttons, drag-to-look only when needed, landscape-safe spacing, and no gesture that conflicts with browser navigation.'}:{})});
  else if(step.id==='loop'){
    const selectedOnlineModes=c.modes.filter(x=>x.startsWith('Online'));
    Object.assign(suggested,{coreLoop:actionLoop,objective:`Complete one readable ${genre.toLowerCase()} route, make at least one consequential risk/reward choice, and reach the result state with progress visible throughout.`,pressure:c.flight?'Rising speed, route collapse, limited boost, and hazards that punish late reads without creating unavoidable collisions.':c.puzzle?'Limited safe rewinds, coupled systems, and escalating spatial complexity without timers during first-time learning.':'Escalating enemy composition, limited recovery, positional risk, and optional high-value encounters.',reward:'Immediate input confirmation, strong audiovisual payoff, score and route feedback, then one small unlock or new tactical option after a completed run.',winFailRetry:'Win by completing the representative route and its final test. Fail on the core resource or health reaching zero. Restart within three seconds; preserve only explicitly earned meta progress.',modes:c.online?['Single-player',...(selectedOnlineModes.length?selectedOnlineModes:['Online co-op'])]:['Single-player','Spectator / replay'],difficulty:'Teach one threat at a time, telegraph every material hazard, guarantee a recovery window after mistakes, and scale composition rather than hidden stat multipliers.',skillExpression:c.flight?'Route knowledge, line choice, speed conservation, boost timing, and deciding when salvage is worth losing the ideal line.':c.puzzle?'Observation, mental modeling, sequencing, spatial planning, and recognizing reusable system rules.':'Timing, aiming, spacing, threat prioritization, route knowledge, and resource tradeoffs.'});
  }
  else if(step.id==='content')Object.assign(suggested,{setting:`A compact, immediately legible world built around ${pitch} Use one dominant landmark, one recurring material motif, and a restrained palette that supports gameplay readability.`,worldStructure:c.flight?'Track / course':c.puzzle?'Room/zone graph':'Authored linear level',firstSlice:`Launch into a title screen, enter one tutorialized space, learn the core verb safely, face two escalating applications, make one optional risk/reward choice, complete a climax, review the result, and retry.`,contentInventory:c.flight?'1 course; 1 player craft; 3 hazard families; 3 pickup types; 2 route branches; 1 climax sequence; title, pause, HUD, fail, and result screens.':c.puzzle?'5 connected rooms; 3 reusable puzzle devices; 1 traversal ability; 2 environmental states; 1 capstone puzzle; title, pause, hint, and completion screens.':'1 level; 1 player actor; 3 enemy roles; 2 abilities or weapons; 3 pickups; 1 elite encounter; 6 VFX families; title, pause, HUD, fail, and result screens.',encounters:'Safe verb introduction → first independent decision → readable threat → reward/recovery beat → combined-system escalation → optional mastery challenge → climax → concise recap.',contentData:'Player tuning, hazards/enemies, abilities, encounter waves, route anchors, rewards, accessibility settings, and UI copy must live in validated definitions rather than scattered scene constants.'});
  else if(step.id==='systems')Object.assign(suggested,{systems,stateBoundaries:'Immutable IDs, tuning, content rules, and authored definitions stay separate from runtime transforms, health/resources, cooldowns, current objectives, and transient presentation state.',...(systems.includes('Combat')?{combatContract:'Actions have explicit startup, active, recovery, and cancel windows. Collision owns contact; the simulation owns damage and invulnerability; presentation reacts to confirmed events only.'}:{}),...(systems.some(x=>['Enemy AI','Navigation / pathfinding'].includes(x))?{aiContract:'NPCs read explicit perception inputs, choose from legal intents, expose state transitions, respect spacing and telegraphs, and run against deterministic test fixtures.'}:{}),...(systems.some(x=>['Progression','Economy / currency'].includes(x))?{progressionContract:'Separate within-run power from persistent unlocks. Cap currency, define every source and sink, and keep permanent bonuses from invalidating the first-run skill test.'}:{}),...(systems.includes('Persistence / saves')?{persistenceContract:'Commit local progress at result screens and settings changes using a versioned schema, validate on load, migrate known versions, and fall back safely without losing defaults.'}:{}),...(systems.includes('Online multiplayer')?{multiplayerContract:'Use server authority for outcome-changing state, explicit room limits, reconnect rules, prediction only where necessary, and never trust client-authored rewards.'}:{})});
  else if(step.id==='presentation')Object.assign(suggested,{artDirection:`Give ${name} a readable shape hierarchy, one signature accent color, restrained surface detail, and strong value separation between player, objective, hazard, and background. Favor authored procedural forms and reusable materials over inconsistent asset volume.`,cameraContract:`Use a ${perspective.toLowerCase()} camera with stable horizon and framing, bounded look input, occlusion handling, critically damped follow motion, configurable shake, and a reduced-motion mode.`,lightingAtmosphere:'Use one clear key-light direction, soft environment fill, selective emissive guidance, distance fog for depth rather than concealment, and quality tiers that preserve gameplay contrast.',visualSystems:c.puzzle?['Exposure / color grading','Scalable shadows','Custom PBR materials']:['Bloom','Exposure / color grading','Scalable shadows','Procedural VFX'],vfxContract:'Every action has anticipation, active, impact, and residue cues with consistent ownership colors. Effects may decorate confirmed events but must never obscure hazards, targets, or navigation.',audioContract:'Layer input confirmation, world response, threat priority, ambience, and adaptive music. Provide subtitle support, independent volume controls, a mute state, and browser audio-unlock handling.',uiStates:'Loading, title, settings, onboarding prompt, gameplay HUD, pause, fail/retry, success/recap, reduced-motion state, input-device change, and asset/runtime error recovery.'});
  else if(step.id==='technical')Object.assign(suggested,{implementationMode:'Lead agent chooses plain Three.js or R3F',browserTargets:`Current stable Chrome, Edge, Firefox, and Safari on desktop; verify ${c.mobile?'one mid-range Android phone in landscape and touch-safe portrait fallback':'integrated graphics and a mid-range discrete GPU'}; degrade unsupported features explicitly.`,performanceBudget:c.mobile?'30 FPS minimum / 60 FPS target on the named mobile baseline; capped DPR; compressed textures; bounded draw calls; under 5 seconds to interactive on broadband.':'60 FPS target at 1080p on the named desktop baseline; capped DPR; bounded draw calls and texture memory; under 3 seconds to interactive on broadband.',simulation:c.action||c.flight?'Fixed timestep + seeded RNG required':'Fixed timestep required; seed optional',physics:c.action||c.flight?'Rapier preferred':'Simple authored collision; no full engine',networking:c.online?'Authoritative online multiplayer':'Offline only',deployment:'Vite production build on GitHub Pages with an explicit base path, hashed static assets, HTTPS, reproducible install/build commands, and no runtime server unless separately approved.',securityPrivacy:'No secrets or privileged API credentials in browser code. Validate imported/local data, constrain external URLs, minimize telemetry, require consent where applicable, and document save-data deletion.'});
  else if(step.id==='assets')Object.assign(suggested,{assetStrategies:['Authored procedural geometry','CC0 / permissive external assets','AI-generated concepts/textures','Hybrid per-asset decision'],licensePolicy:'CC0 + permissive commercial licenses',heroAssets:'Player/craft silhouette, signature interaction tool, primary threat, final encounter landmark, environment identity piece, HUD identity, and one signature audio motif.',assetBudgets:'Define per-model triangle and texture limits during preflight; use KTX2 and mesh optimization where measured; require LODs only for assets that materially affect frame time; keep the first-slice compressed payload bounded.',externalServices:'Prefer local/procedural and permissively licensed sources. Paid generation requires explicit approval and environment-provided credentials; every unavailable service needs a no-cost fallback.',dependencyConstraints:'Preserve an existing lockfile; prefer maintained ESM packages; pin intentional versions; justify runtime weight; prohibit client secrets; remove dependencies that do not survive a measured preflight.',feasibilityLedger:'Spike camera/controls and the highest-risk simulation or rendering assumption first. Owner: lead agent. Trigger: before content production. Defer only nonblocking polish with a named owner and acceptance-stage resolution trigger.',provenanceManifest:'Required for every shipped asset'});
  else if(step.id==='verification')Object.assign(suggested,{primaryJourney:`Launch ${name} → start the first slice → learn the core verb → complete one representative challenge → pause/resume → fail/retry → finish → inspect the result screen.`,acceptanceCriteria:`A new player completes the representative slice without external instructions.\nExisting answers and imported drafts survive reload without schema-invalid values.\nThe same seed and inputs reproduce the same simulation outcome where determinism is required.\nThe production preview has no console errors, missing assets, broken controls, or blocked primary interactions.`,automatedGates:['Typecheck','Unit tests','Deterministic simulation tests','Browser smoke tests','Accessibility scan','Bundle-size gate','Performance trace'],capturePlan:'Capture fixed title, onboarding, representative gameplay, maximum-load, fail, and success views; record the complete primary journey; save a target-device frame-time trace and accessibility report against the exact commit.',hardFailures:'Broken primary journey, console errors, missing assets, inaccessible controls, secret exposure, unlicensed content, non-reproducible build, or target-device performance below the declared floor.',definitionOfDone:'The deployed exact commit passes every automated gate and primary journey, independent critics approve each important piece against the quality bar, provenance is recorded, and limitations are explicit.'});
  else if(step.id==='budget')Object.assign(suggested,{harness:'Either — lead chooses',effort:'High',timeLimitHours:8,spendLimitUsd:100,tokenLimitMillions:10,budgetScope:'All lead + subagent model usage; paid APIs require separate approval',budgetEnforcement:'Harness telemetry plus coordinator checkpoints',maxConcurrency:4,reservePercent:20,checkpointMinutes:30,plateauPolicy:'Pause for approval with the best next experiment',limitFallback:'Enforce wall time + concurrency; report estimates'});
  else if(step.id==='handoff')Object.assign(suggested,{packageManager:'Preserve existing lockfile',deliveryRule:'Work on a feature branch or isolated worktree, use reviewable commits, never push directly to the protected default branch, and report the exact final commit plus preview/deployment URL.',humanApproval:'Approval is required before paid API use, public publishing, destructive migration, credential changes, or raising any declared run ceiling.',openQuestions:'None. If inspection reveals a blocking conflict, stop and present the smallest decision needed with evidence.',finalNotes:`Keep ${name}'s agreed first slice and quality bar authoritative. Prefer reversible changes, preserve existing project conventions, and record evidence rather than substituting summaries.`});
  const allowed=new Set(step.fields.map(f=>f.id)),patch={};
  Object.entries(suggested).forEach(([id,value])=>{if(allowed.has(id)&&!valuePresent(a[id])&&valuePresent(value))patch[id]=value});
  return patch;
}
function applyLuckySuggestions(){
  const patch=buildLuckySuggestions(STEPS[state.currentStep]),entries=Object.entries(patch);
  if(!entries.length){showToast('No unanswered fields on this stage can be suggested');return}
  entries.forEach(([id,value])=>{state.answers[id]=value});saveState();render();showToast(`Added ${entries.length} editable suggestion${entries.length===1?'':'s'} — existing answers untouched`);
}

function routed(){
  const resources=[],skills=[];const seenR=new Set(),seenS=new Set();
  WORKFLOW.resourceRules.forEach(rule=>{
    const v=state.answers[rule.field];const match=rule.always||((Array.isArray(v)?v.some(x=>String(x).includes(rule.contains)):String(v||'').includes(rule.contains)));
    if(!match)return;
    (rule.resources||[]).forEach(r=>{if(!seenR.has(r.name)){seenR.add(r.name);resources.push(r)}});
    (rule.skills||[]).forEach(s=>{if(!seenS.has(s)){seenS.add(s);skills.push(s)}});
  });
  return {resources,skills};
}
function renderInspector(){
  const pct=completion(),issues=allIssues(),step=STEPS[state.currentStep],stepMiss=stepMissing(step),route=routed();
  $('#ring').style.setProperty('--p',pct);$('#ringText').textContent=pct+'%';$('#statusTitle').textContent=issues.length?'Draft':'Handoff ready';$('#statusCopy').textContent=issues.length?`${issues.length} decision${issues.length===1?'':'s'} need attention`:'Canon can be exported';
  $('#missingList').innerHTML=stepMiss.length?stepMiss.map(f=>`<li>${esc(f.label)}</li>`).join(''):'<li style="color:var(--green)">This step is complete.</li>';
  $('#routeList').innerHTML=route.resources.slice(0,7).map(r=>`<div class="route"><b><a target="_blank" rel="noopener" href="${esc(r.url)}">${esc(r.name)}</a></b><span>${esc(r.role)}</span></div>`).join('')||'<div class="help">Select systems and asset strategies to route resources.</div>';
  $('#skillTags').innerHTML=route.skills.slice(0,16).map(s=>`<span class="skill-tag">${esc(s)}</span>`).join('')||'<span class="help">Skills appear as the specification becomes concrete.</span>';
}
function renderFinal(){
  const ready=allIssues().length===0,panel=$('#finalPanel');panel.classList.toggle('locked',!ready);
  $$('[data-export]').forEach(b=>{b.disabled=!ready&&b.dataset.export!=='json'});
  $('#finalTitle').textContent=ready?'Specification locked. Export the implementation runway.':'Handoff exports unlock when the required decisions are complete.';
  $('#finalDescription').textContent=ready?'The spec is closed enough for agent execution. The lead still chooses decomposition and architecture inside your constraints.':'You can export a draft at any time. Complete every required decision before treating it as implementation-ready.';
  $('#promptPreview').textContent=buildShortPrompt();
}

function normalizedBudget(){
  const a=state.answers,enforcement=a.budgetEnforcement||'',readNumber=id=>{const f=ALL_FIELDS.find(field=>field.id===id),v=a[id];return f&&fieldValueValid(f,v)?v:null};
  const hours=readNumber('timeLimitHours'),spend=readNumber('spendLimitUsd'),tokens=readNumber('tokenLimitMillions'),concurrency=readNumber('maxConcurrency'),reserve=readNumber('reservePercent'),checkpoint=readNumber('checkpointMinutes');
  const level=enforcement.startsWith('Launcher / gateway')?'hard':enforcement.startsWith('Harness telemetry')?'telemetry_dependent':enforcement.startsWith('Prompt-only')?'best_effort':'unknown';
  const activeLimits=[];if(hours!==null&&hours>0)activeLimits.push('wallClockSeconds');if(spend!==null&&spend>0)activeLimits.push('spendLimitUsd');if(tokens!==null&&tokens>0)activeLimits.push('tokenLimit');if(concurrency!==null&&concurrency>0)activeLimits.push('maxConcurrency');
  return {wallClockSeconds:hours===null?null:hours*3600,spendLimitUsd:spend,tokenLimit:tokens===null?null:tokens*1000000,maxConcurrency:concurrency,integrationReservePercent:reserve,checkpointSeconds:checkpoint===null?null:checkpoint*60,scope:a.budgetScope||'',enforcementMode:enforcement,enforcementLevel:level,mandatoryStopConditions:['quality_bar_met','first_declared_budget_ceiling','human_cancellation','blocking_dependency_or_unsafe_ambiguity','infrastructure_failure'],plateauPolicy:a.plateauPolicy||'',unknownTelemetryBehavior:a.limitFallback||'',hardLimits:level==='hard'?activeLimits:[],telemetryDependentLimits:level==='telemetry_dependent'?activeLimits:[],bestEffortLimits:level==='best_effort'?activeLimits:[]};
}
function buildJsonExport(){
  const route=routed(),issues=allIssues();return {schemaVersion:WORKFLOW.meta.version,status:issues.length?'draft':'ready',createdAt:state.startedAt,updatedAt:state.updatedAt,completionPercent:completion(),answers:state.answers,routing:route,gauntlet:{qualityBar:state.answers.barSentence||'',referenceUrls:lines(state.answers.referenceUrls),budget:normalizedBudget(),directive:buildShortPrompt()},validationIssues:issues.map(f=>({step:f.stepTitle,field:f.label}))};
}
function answerSection(step){
  const rows=step.fields.map(f=>`| ${md(f.label)} | ${md(valuePresent(state.answers[f.id])?asText(state.answers[f.id]):'_Open_')} |`).join('\n');
  return `## ${step.eyebrow} — ${step.title}\n\n| Decision | Canon |\n|---|---|\n${rows}`;
}
function md(s){return String(s??'').replace(/\|/g,'\\|').replace(/\r?\n/g,'<br>')}
function budgetContract(){
  const a=state.answers;const spend=Number(a.spendLimitUsd||0),tokens=Number(a.tokenLimitMillions||0),time=Number(a.timeLimitHours||0),reserve=Number(a.reservePercent||0);
  return `## Gauntlet budget governor\n\n- **Wall-clock ceiling:** ${time} hours\n- **Spend ceiling:** ${spend?`$${spend.toFixed(2)}`:'not measured; report unknown'}\n- **Token ceiling:** ${tokens?`${tokens} million aggregate lead + subagent tokens`:'not measured; report unknown'}\n- **Spend scope:** ${a.budgetScope||'—'}\n- **Enforcement mode:** ${a.budgetEnforcement||'—'}\n- **Maximum concurrent subagents:** ${a.maxConcurrency||'open'}\n- **Integration/final-QA reserve:** ${reserve}%\n- **Checkpoint cadence:** every ${a.checkpointMinutes||'—'} minutes\n- **Plateau policy:** ${a.plateauPolicy||'—'}\n- **Unknown-telemetry behavior:** ${a.limitFallback||'—'}\n\nMandatory stop conditions are: the quality bar is met; the first applicable declared ceiling is reached under its available meter and enforcement; human cancellation; a blocking dependency or unsafe ambiguity; or infrastructure failure. At a ceiling, stop immediately and preserve the runnable state—do not continue an atomic change past the limit. Apply the selected plateau policy only when fresh critic evidence shows no feasible high-impact improvement remains—not from agent confidence alone. A ceiling is hard only when a launcher or gateway actually enforces it. Harness/coordinator limits are telemetry-dependent; prompt-only limits are best-effort. Unknown usage stays \`unknown\`—never invent precision. At ${(100-reserve)}% of any measurable ceiling, stop opening new component loops and spend only the reserved capacity on reconciliation, regression repair, artifact inspection, evidence capture, progress finalization, and leaving a runnable handoff. The reserve is not available for speculative iteration.`;
}
function routingMarkdown(){
  const r=routed();
  const resources=r.resources.map(x=>`- [${x.name}](${x.url}) — ${x.role}`).join('\n')||'- No resources routed yet.';
  const skills=r.skills.map(x=>`- \`${x}\``).join('\n')||'- No specialist skills routed yet.';
  return `## Routed resource and skill candidates\n\nThese are preflight candidates, not mandatory architecture. The lead agent must inspect the workspace, justify what it uses, preserve an existing stack where appropriate, and substitute only with recorded rationale.\n\n### Resources / dependencies to inspect\n${resources}\n\n### Agent skills to load when available\n${skills}`;
}
function preflightContract(){
  return `## Dependency preflight contract\n\nBefore gameplay implementation, the lead agent must inspect the actual workspace and write \`docs/gauntlet/DEPENDENCY_PREFLIGHT.md\` containing:\n\n1. repository/branch/worktree status, baseline artifacts, fixed constraints, and existing build/runtime path;\n2. selected package manager and preserved lockfile policy;\n3. renderer, physics, state, AI/navigation, networking, UI, audio, asset-pipeline, test, browser-automation, profiling, and deployment needs — marking each as required, optional, existing, added, substituted, or rejected;\n4. relevant routed skill packs and whether they are installed/readable;\n5. environment variables, external APIs/MCPs, license/provenance requirements, and approval gates — never secret values;\n6. verified commands for install, typecheck, tests, production build, local preview, browser smoke test, and deployment;\n7. the actual launcher/telemetry path for every claimed hard or measured budget ceiling, downgrading unsupported claims to best-effort;\n8. feasibility spikes, deferred non-blockers with owner/trigger, blockers, and reversible fallbacks.\n\nThe lead may install normal project dependencies and create local build/test scaffolding. It must stop for human approval before paid API use, public publishing, destructive migration, credential changes, or raising a run ceiling.`;
}
function buildMarkdown(){
  const route=routed(),issues=allIssues();
  return `# ${state.answers.title||'Untitled Three.js Game'} — Canonical Game Specification\n\n> **Status:** ${issues.length?'DRAFT — '+issues.length+' decisions need attention':'READY FOR HANDOFF'}  \n> **Schema:** Spec Forge ${WORKFLOW.meta.version}  \n> **Updated:** ${state.updatedAt}\n\n${STEPS.map(answerSection).join('\n\n')}\n\n${routingMarkdown()}\n\n${preflightContract()}\n\n${budgetContract()}\n\n## Validation issues\n\n${issues.length?issues.map(f=>`- **${f.stepTitle}:** ${f.label}`).join('\n'):'None. Optional notes may still remain blank.'}\n\n## Authority and change control\n\nThis file is the product canon for the implementation run. The lead agent may choose architecture and decomposition inside these constraints, but it must not silently rewrite locked product rules. Record any unavoidable conflict, proposed change, and its impact before proceeding.\n`;
}
function buildShortPrompt(){
  const a=state.answers,route=routed(),refs=lines(a.referenceUrls).join(', ')||'[reference URLs in GAME_SPEC.md]';
  return `Build ${a.title||'the Three.js game'} from the attached GAME_SPEC.md. Its product decisions are canon; choose the implementation approach and exact decomposition inside those constraints.\n\nBefore coding, inspect the real workspace and complete the dependency preflight in the spec. Resolve reversible dependencies, verify the build/browser path, validate every claimed enforcement mechanism, and stop at the named approval gates.\n\nQuality bar: ${a.barSentence||a.visualBar||'[quality bar in GAME_SPEC.md]'} References: ${refs}.\n\nRun a Gauntlet Loop: split the game into the smallest important pieces that can be built and judged independently. For each piece, fan out a builder and a separate critic with fresh context. Builders use isolated branches/worktrees; only one integration owner mutates the shared runnable branch. Critics receive fresh context and inspect immutable runnable artifacts—the actual game pixels, audio, tests, or traces—then compare directly with the bar using blind A/B when possible, name the largest remaining gap, and send it back. The builder never grades itself. Use a fresh integration critic after major waves.\n\nMaintain a live progress page showing exact/estimated/unknown usage, active roles, artifact and commit identity, captures, tests, wins, remaining gaps, reserve state, next admitted action, and stop forecast. Use subagents with ${a.effort||'the highest appropriate effort'}, at most ${a.maxConcurrency||4} concurrently. Stop immediately when the quality bar is met, the first applicable declared ceiling is reached under its selected enforcement, I cancel, a dependency or ambiguity blocks safe work, infrastructure fails, or the selected plateau policy requires it. Requested ceilings: ${a.timeLimitHours||'—'} hours, ${Number(a.spendLimitUsd||0)?'$'+a.spendLimitUsd:'spend telemetry unavailable'}, ${Number(a.tokenLimitMillions||0)?a.tokenLimitMillions+'M tokens':'token telemetry unavailable'}; enforcement: ${a.budgetEnforcement||'specified in GAME_SPEC.md'}. Reserve ${a.reservePercent||20}% exclusively for integration and final verification; never raise a limit without approval and never fabricate unknown usage.\n\nFinish with a deployed or locally runnable exact commit, evidence against every acceptance gate, dependency/license provenance, known limitations, a machine-readable budget stop record, and reproduction commands.`;
}
function buildSelfContainedPrompt(){return `${buildShortPrompt()}\n\n---\n\n# ATTACHED GAME_SPEC.md\n\n${buildMarkdown()}`}
function buildPacket(){
  return `# ${state.answers.title||'Three.js Game'} — Agent Implementation Packet\n\n## Lead-agent directive\n\n${buildShortPrompt()}\n\n## Mandatory dependency runway\n\n${preflightContract()}\n\n${budgetContract()}\n\n## Canonical specification\n\n${buildMarkdown()}\n\n## Required final report\n\n- exact branch, commit, and deployed/preview URL;\n- dependency and skill changes with rationale;\n- commands run and real results;\n- quality-bar comparison evidence by independently judged piece;\n- budget usage/estimates and stop reason;\n- known limitations, open risks, and the next highest-value gap.\n`;
}
function handleExport(kind){
  const ready=allIssues().length===0;
  if(!ready&&kind!=='json'){showToast('Complete all required decisions before final handoff');return}
  const base=slug(state.answers.title);
  if(kind==='spec')download(`${base}-GAME_SPEC.md`,buildMarkdown(),'text/markdown');
  if(kind==='prompt')copyText(buildSelfContainedPrompt(),'Self-contained handoff copied');
  if(kind==='packet')download(`${base}-IMPLEMENTATION_PACKET.md`,buildPacket(),'text/markdown');
  if(kind==='json')download(`${base}-GAME_SPEC.json`,JSON.stringify(buildJsonExport(),null,2),'application/json');
}
function download(name,text,type){const blob=new Blob([text],{type:`${type};charset=utf-8`});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),500);showToast(`Downloaded ${name}`)}
async function copyText(text,msg){try{await navigator.clipboard.writeText(text);showToast(msg)}catch{const ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();showToast(msg)}}
function importDraft(e){
  const file=e.target.files?.[0];if(!file)return;const reader=new FileReader();reader.onload=()=>{try{const data=JSON.parse(reader.result);const answers=data.answers||data.state?.answers;if(!answers||typeof answers!=='object'||Array.isArray(answers))throw new Error('No answers object');state={...DEFAULT_STATE,answers:normalizeAnswers(answers),currentStep:0,startedAt:typeof data.createdAt==='string'?data.createdAt:new Date().toISOString(),updatedAt:new Date().toISOString()};applyDefaults();saveState();render();showToast(allIssues().length?'Draft imported — review highlighted values':'Draft imported')}catch(err){console.error(err);showToast('Invalid Spec Forge JSON')}};reader.readAsText(file);e.target.value='';
}
init();
</script>
</body>
</html>
'''.replace('__DATA__', data_json)


if __name__ == "__main__":
    main()

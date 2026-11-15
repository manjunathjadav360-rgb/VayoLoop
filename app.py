from __future__ import annotations

import base64
import csv
import io
import json
import os
from datetime import datetime, time, timedelta

import streamlit as st
import streamlit.components.v1 as components

from vayoloop_core import (
    INDIA_TZ,
    analyse_health_trends,
    acknowledge_emergency_contact,
    close_emergency_event,
    create_emergency_event,
    escalate_emergency,
    india_now,
    medication_state,
    record_dose,
    seed_demo_state,
)

from vayoloop_db import (
    DEFAULT_SUPABASE_PUBLISHABLE_KEY,
    DEFAULT_SUPABASE_URL,
    create_supabase_client,
    delete_prescription_record,
    download_prescription_file,
    list_health_observations,
    list_prescription_records,
    save_health_observation,
    save_prescription_record,
)
from care_passport import build_care_passport, render_care_passport_html
from vayoloop_security import html_text, json_for_script

st.set_page_config(
    page_title="VayoLoop — Care beyond reminders",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

VOICE_LANGUAGES = {
    "English (India)": "en-IN",
    "हिन्दी": "hi-IN",
    "ಕನ್ನಡ": "kn-IN",
    "ગુજરાતી": "gu-IN",
    "मराठी": "mr-IN",
    "தமிழ்": "ta-IN",
    "తెలుగు": "te-IN",
    "বাংলা": "bn-IN",
}

VOICE_COPY = {
    "en-IN": {"due": "It is time for your scheduled medicine reminder. Please check your care plan.", "follow": "Your scheduled medicine reminder is still awaiting a report. Please check your care plan.", "appointment": "You have an appointment coming up in about one hour. Please check the appointment details."},
    "hi-IN": {"due": "आपकी दवा की तय याद दिलाने का समय है। कृपया अपनी देखभाल योजना देखें।", "follow": "दवा की याद अभी रिपोर्ट नहीं हुई है। कृपया अपनी देखभाल योजना देखें।", "appointment": "लगभग एक घंटे में आपकी अपॉइंटमेंट है। कृपया जानकारी देखें।"},
    "kn-IN": {"due": "ನಿಮ್ಮ ಔಷಧಿ ನೆನಪಿಸುವ ಸಮಯವಾಗಿದೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಆರೈಕೆ ಯೋಜನೆಯನ್ನು ಪರಿಶೀಲಿಸಿ.", "follow": "ಔಷಧಿ ವರದಿ ಇನ್ನೂ ದಾಖಲಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಆರೈಕೆ ಯೋಜನೆಯನ್ನು ಪರಿಶೀಲಿಸಿ.", "appointment": "ಸುಮಾರು ಒಂದು ಗಂಟೆಯಲ್ಲಿ ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಇದೆ. ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."},
    "gu-IN": {"due": "તમારી દવાની યાદ અપાવવાનો સમય થયો છે. કૃપા કરીને તમારી સંભાળ યોજના તપાસો.", "follow": "દવાની નોંધ હજી કરવામાં આવી નથી. કૃપા કરીને તમારી સંભાળ યોજના તપાસો.", "appointment": "લગભગ એક કલાકમાં તમારી મુલાકાત છે. કૃપા કરીને વિગતો તપાસો."},
    "mr-IN": {"due": "तुमच्या औषधाची आठवण करून देण्याची वेळ झाली आहे. कृपया तुमची काळजी योजना तपासा.", "follow": "औषधाची नोंद अजून झालेली नाही. कृपया काळजी योजना तपासा.", "appointment": "सुमारे एका तासात तुमची भेट आहे. कृपया तपशील तपासा."},
    "ta-IN": {"due": "உங்கள் மருந்து நினைவூட்டும் நேரம் வந்துவிட்டது. உங்கள் பராமரிப்பு திட்டத்தைப் பார்க்கவும்.", "follow": "மருந்து பதிவு இன்னும் செய்யப்படவில்லை. உங்கள் பராமரிப்பு திட்டத்தைப் பார்க்கவும்.", "appointment": "சுமார் ஒரு மணி நேரத்தில் உங்களுக்கு சந்திப்பு உள்ளது. விவரங்களைப் பார்க்கவும்."},
    "te-IN": {"due": "మీ మందుల రిమైండర్ సమయం వచ్చింది. దయచేసి మీ సంరక్షణ ప్రణాళికను చూడండి.", "follow": "మందుల నమోదు ఇంకా చేయలేదు. దయచేసి మీ సంరక్షణ ప్రణాళికను చూడండి.", "appointment": "సుమారు గంటలో మీ అపాయింట్‌మెంట్ ఉంది. వివరాలు చూడండి."},
    "bn-IN": {"due": "আপনার ওষুধের নির্ধারিত সময় হয়েছে। অনুগ্রহ করে আপনার যত্নের পরিকল্পনা দেখুন।", "follow": "ওষুধের রিপোর্ট এখনও করা হয়নি। অনুগ্রহ করে আপনার যত্নের পরিকল্পনা দেখুন।", "appointment": "প্রায় এক ঘণ্টার মধ্যে আপনার অ্যাপয়েন্টমেন্ট আছে। অনুগ্রহ করে বিস্তারিত দেখুন।"},
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
        :root { --vl-ink:#20352e; --vl-muted:#718078; --vl-paper:#f5f2e9; --vl-green:#245b49; --vl-green2:#326e58; --vl-line:#e7e4da; --vl-card:#fffefa; --vl-soft:#eaf0e8; --vl-amber:#f7efdf; --vl-red:#f7e9e5; }
        html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
        .stApp { background:var(--vl-paper); color:var(--vl-ink); }
        [data-testid="stHeader"] { background:rgba(245,242,233,.88); }
        [data-testid="stSidebar"] { background:#eeeae0; border-right:1px solid #dfded3; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#52645a; }
        [data-testid="stSidebar"] .stRadio label { font-weight:600; padding:3px 0; }
        h1,h2,h3 { font-family:'Manrope',sans-serif; color:var(--vl-ink); letter-spacing:-.035em; }
        h1 { font-weight:800; }
        h2 { font-size:1.28rem; font-weight:750; }
        h3 { font-size:1.02rem; font-weight:750; }
        p, label, .stCaption { color:#64736a; }
        [data-testid="stMetric"] { background:var(--vl-card); border:1px solid var(--vl-line); border-radius:12px; padding:14px 16px; box-shadow:0 4px 16px rgba(35,53,44,.035); }
        [data-testid="stMetricLabel"] { color:#77847b; font-size:.76rem; font-weight:700; }
        [data-testid="stMetricValue"] { color:var(--vl-green); font-family:'Manrope',sans-serif; font-weight:800; }
        [data-testid="stMetricDelta"] { font-size:.72rem; }
        [data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--vl-line)!important; border-radius:13px!important; background:var(--vl-card); }
        .vl-hero { background:#244d3f; color:#fff; border-radius:15px; padding:25px 28px; margin:4px 0 18px; display:flex; justify-content:space-between; gap:18px; align-items:center; }
        .vl-hero .kicker { color:#c9d9cb; letter-spacing:.16em; font-size:.67rem; font-weight:800; text-transform:uppercase; }
        .vl-hero h1 { color:#fff; margin:7px 0 5px; font-size:clamp(1.8rem,3.5vw,2.5rem); }
        .vl-hero p { color:#d9e3da; margin:0; font-size:.91rem; }
        .vl-hero .hero-mark { font:800 3.1rem 'Manrope'; color:#d9e5d8; opacity:.95; border:1px solid rgba(255,255,255,.22); border-radius:50%; width:76px; height:76px; display:grid; place-items:center; flex:none; }
        .vl-demo { display:flex; gap:8px; align-items:center; background:#f2ecdc; color:#76613d; border:1px solid #e6ddc9; padding:8px 12px; border-radius:8px; font-size:.75rem; margin:0 0 14px; }
        .vl-dot { width:7px; height:7px; background:#ba8b3c; border-radius:50%; display:inline-block; flex:none; }
        .vl-section-label { text-transform:uppercase; letter-spacing:.13em; color:var(--vl-green); font-weight:800; font-size:.67rem; margin:8px 0 7px; }
        .vl-card-title { font:750 1rem 'Manrope'; color:var(--vl-ink); margin-bottom:4px; }
        .vl-muted { color:var(--vl-muted); font-size:.82rem; line-height:1.55; }
        .vl-pill { display:inline-block; border-radius:20px; padding:4px 9px; background:var(--vl-soft); color:var(--vl-green); font-size:.68rem; font-weight:800; }
        .vl-pill.warn { background:var(--vl-amber); color:#89662e; }
        .vl-pill.red { background:var(--vl-red); color:#954a40; }
        .vl-note { border-left:3px solid #73977d; background:#f0f3eb; padding:10px 12px; border-radius:0 8px 8px 0; color:#506458; font-size:.78rem; line-height:1.55; }
        .vl-danger { border-left-color:#ad5548; background:#f8efea; color:#75443e; }
        .vl-small { color:#849087; font-size:.7rem; }
        .stButton > button, .stLinkButton > a { border-radius:8px; font-weight:700; min-height:2.55rem; }
        .stButton > button[kind="primary"] { background:var(--vl-green); border-color:var(--vl-green); }
        .stButton > button[kind="primary"]:hover { background:var(--vl-green2); border-color:var(--vl-green2); }
        .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input, .stSelectbox div[data-baseweb="select"] { border-radius:8px; }
        div[data-testid="stExpander"] { border-color:var(--vl-line); border-radius:10px; background:var(--vl-card); }
        hr { border-color:var(--vl-line); }
        [data-testid="stDataFrame"] { border:1px solid var(--vl-line); border-radius:9px; }
        footer { visibility:hidden; }
        @media(max-width:720px){ .vl-hero{padding:20px;}.vl-hero .hero-mark{width:54px;height:54px;font-size:2.2rem;} }
        </style>
        """,
        unsafe_allow_html=True,
    )


def voice_companion_html(meds: list[dict], appointments: list[dict], language: str) -> str:
    lang_copy = VOICE_COPY.get(language, VOICE_COPY["en-IN"])
    active_meds = []
    today = india_now().date().isoformat()
    reports = st.session_state.workspace["dose_reports"]
    for med in meds:
        reported = any(r["medication_id"] == med["id"] and r["reported_at"][:10] == today for r in reports)
        if med.get("active", True):
            active_meds.append({"id": med["id"], "time": med["time"], "reported": reported})
    upcoming = [
        {"id": appt["id"], "when": appt["when"]}
        for appt in appointments if appt["status"] == "Scheduled"
    ]
    data = json_for_script({"meds": active_meds, "appointments": upcoming, "copy": lang_copy, "language": language})
    greeting = json_for_script("Hi Asha, welcome back.")
    return """
    <div id="voicePanel" style="font-family:Arial,sans-serif;background:#f8f8f1;border:1px solid #e3e5d9;border-radius:10px;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px;color:#30473b">
      <div style="min-width:0"><div style="font-size:12px;font-weight:700">VayoLoop voice companion</div><div id="voiceStatus" style="font-size:11px;color:#718078;margin-top:3px">Welcome and scheduled reminders can be spoken when audio is enabled.</div></div>
      <button id="voiceEnable" style="flex:none;border:0;border-radius:7px;background:#245b49;color:white;padding:9px 12px;font-weight:700;font-size:11px">Enable voice alerts</button>
    </div>
    <script>
    (function(){
      const config = """ + data + """;
      const greeting = """ + greeting + """;
      const enable = document.getElementById('voiceEnable');
      const status = document.getElementById('voiceStatus');
      let timer = null;
      let audioContext = null;
      function setStatus(message){ status.textContent = message; }
      function speak(message){
        if(!('speechSynthesis' in window)) { setStatus('Speech is not supported in this browser.'); return; }
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(message);
        const voices = window.speechSynthesis.getVoices();
        const preferred = voices.find(v => v.lang.toLowerCase() === config.language.toLowerCase()) || voices.find(v => v.lang.toLowerCase().startsWith(config.language.slice(0,2).toLowerCase())) || voices.find(v => v.lang.toLowerCase().startsWith('en'));
        if(preferred) utterance.voice = preferred;
        utterance.lang = preferred ? preferred.lang : config.language;
        utterance.rate = 0.88; utterance.pitch = 1; utterance.volume = 1;
        utterance.onstart = () => setStatus('Speaking. Scheduled reminders are checked while this page stays open.');
        utterance.onend = () => setStatus('Voice alerts enabled · reminders are checked while this page stays open.');
        utterance.onerror = () => setStatus('Browser audio was blocked or unavailable. Tap Enable voice alerts again.');
        window.speechSynthesis.speak(utterance);
      }
      function ring(){
        try{
          const AudioClass = window.AudioContext || window.webkitAudioContext;
          if(!AudioClass) return;
          if(!audioContext) audioContext = new AudioClass();
          if(audioContext.state === 'suspended') audioContext.resume();
          [0,0.24].forEach(offset=>{
            const osc = audioContext.createOscillator();
            const gain = audioContext.createGain();
            const start = audioContext.currentTime + offset;
            osc.type='sine'; osc.frequency.setValueAtTime(720,start);
            gain.gain.setValueAtTime(0.0001,start);
            gain.gain.exponentialRampToValueAtTime(0.12,start+0.03);
            gain.gain.exponentialRampToValueAtTime(0.0001,start+0.19);
            osc.connect(gain); gain.connect(audioContext.destination);
            osc.start(start); osc.stop(start+0.2);
          });
        }catch(e){ setStatus('The browser could not play the alert tone.'); }
      }
      function announce(key, text){
        try{
          if(localStorage.getItem(key)) return;
          localStorage.setItem(key,'1');
        }catch(e){}
        ring(); speak(text);
      }
      function check(){
        const now = new Date();
        const dayKey = now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')+'-'+String(now.getDate()).padStart(2,'0');
        const minuteNow = now.getHours()*60+now.getMinutes();
        config.meds.forEach(med=>{
          if(med.reported) return;
          const parts = med.time.split(':').map(Number);
          const dueMinute = parts[0]*60+parts[1];
          const diff = minuteNow-dueMinute;
          if(diff >= 0 && diff <= 29) announce('vayoloop_dose_'+med.id+'_'+dayKey, config.copy.due);
          if(diff >= 30 && diff <= 90) announce('vayoloop_follow_'+med.id+'_'+dayKey, config.copy.follow);
        });
        config.appointments.forEach(appt=>{
          const when = new Date(appt.when);
          const minutes = (when.getTime()-now.getTime())/60000;
          if(minutes > 0 && minutes <= 60) announce('vayoloop_appt_'+appt.id, config.copy.appointment);
        });
      }
      function start(){
        if(timer) clearInterval(timer);
        check();
        timer = setInterval(check,15000);
        enable.textContent='Voice alerts enabled';
        setStatus('Voice alerts enabled · reminders are checked every 15 seconds while this page stays open.');
      }
      enable.addEventListener('click',function(){
        try{ localStorage.setItem('vayoloop_voice_enabled','1'); }catch(e){}
        try{
          const AudioClass = window.AudioContext || window.webkitAudioContext;
          if(AudioClass){ if(!audioContext) audioContext=new AudioClass(); if(audioContext.state==='suspended') audioContext.resume(); }
        }catch(e){}
        speak(greeting);
        start();
      });
      try{
        if(localStorage.getItem('vayoloop_voice_enabled')==='1'){
          enable.textContent='Voice alerts active';
          setTimeout(function(){ speak(greeting); start(); },250);
        }
      }catch(e){}
    })();
    </script>
    """


def fmt_datetime(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone(INDIA_TZ).strftime("%a, %d %b · %I:%M %p")
    except (ValueError, TypeError):
        return "Time not set"


def health_records_csv(records: list[dict]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["record_id", "observation", "value", "unit", "observed_at", "source"])
    for item in sorted(records, key=lambda value: value.get("observed_at", "")):
        writer.writerow([
            item.get("id", ""), item.get("metric", ""), item.get("value", ""),
            item.get("unit", ""), item.get("observed_at", ""), item.get("source", ""),
        ])
    return buffer.getvalue()


def add_event(title: str, detail: str) -> None:
    st.session_state.workspace["events"].insert(
        0, {"id": f"evt-{datetime.now().timestamp()}", "title": title, "detail": detail, "at": india_now().isoformat()}
    )


def active_emergency_events() -> list[dict]:
    closed = {"Closed · person confirmed okay", "Closed · demo resolved"}
    return [event for event in st.session_state.workspace["emergency_events"] if event["status"] not in closed]


def update_emergency_event(updated: dict) -> None:
    events = st.session_state.workspace["emergency_events"]
    for index, event in enumerate(events):
        if event["id"] == updated["id"]:
            events[index] = updated
            return


def status_badge(status: str) -> str:
    if "Overdue" in status or "Urgent" in status or "Awaiting" in status:
        return "🔸"
    if "Reported" in status or "acknowledged" in status.lower() or "Closed" in status:
        return "✓"
    return "•"


def navigate_to_section(section_name: str) -> None:
    st.session_state.workspace_section = section_name





def connect_demo_database():
    """Connect without sign-in to the one shared, fictional public demo workspace."""
    if os.getenv("VAYOLOOP_DISABLE_PERSISTENCE") == "1":
        return None
    if "vayoloop_demo_db_client" in st.session_state:
        return st.session_state.vayoloop_demo_db_client

    project_url = DEFAULT_SUPABASE_URL
    publishable_key = DEFAULT_SUPABASE_PUBLISHABLE_KEY
    try:
        project_url = str(st.secrets.get("SUPABASE_URL", project_url)).strip()
        publishable_key = str(
            st.secrets.get("SUPABASE_PUBLISHABLE_KEY", publishable_key)
        ).strip()
    except Exception:
        pass

    try:
        client = create_supabase_client(project_url, publishable_key)
        st.session_state.vayoloop_demo_db_client = client
        return client
    except Exception:
        return None


if "workspace" not in st.session_state:
    st.session_state.workspace = seed_demo_state()
if "role" not in st.session_state:
    st.session_state.role = "Elder"
if "voice_language" not in st.session_state:
    st.session_state.voice_language = "English (India)"
if "large_text" not in st.session_state:
    st.session_state.large_text = False


inject_styles()

cloud_client = connect_demo_database()
cloud_active = False
cloud_error = None

with st.sidebar:
    st.markdown("**SHARED DEMO WORKSPACE**")
    if cloud_client is not None:
        try:
            # A small read confirms that the database and API permissions are live.
            list_health_observations(cloud_client)
            cloud_active = True
            st.caption("Cloud storage connected · shared fictional data")
        except Exception as exc:
            cloud_error = str(exc)
            st.caption("Cloud storage temporarily unavailable")
    else:
        st.caption("Cloud storage is disabled in automated tests.")
    st.markdown("---")
    st.markdown(
        "<div style='display:flex;align-items:center;gap:10px;margin:6px 0 20px'><div style='background:#245b49;color:white;border-radius:11px;width:40px;height:40px;display:grid;place-items:center;font:800 20px Manrope'>V</div><div><div style='font:800 19px Manrope;color:#20352e;letter-spacing:-.05em'>VayoLoop</div><div style='font-size:9px;letter-spacing:.16em;color:#78847a;font-weight:800'>CARE BEYOND REMINDERS</div></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("**DEMO WORKSPACE**")
    st.selectbox("Preview perspective", ["Elder", "Family", "Caregiver", "Viewer"], key="role")
    language_label = st.selectbox("Voice reminder language", list(VOICE_LANGUAGES), key="voice_language")
    st.toggle("Larger text", key="large_text")
    st.markdown("---")
    section = st.radio(
        "Workspace",
        ["Home", "Medicines", "Prescription library", "Health journal", "Appointments", "Family circle", "Emergency centre", "Connected living", "Local support", "Care Passport"],
        label_visibility="visible",
        key="workspace_section",
    )
    st.markdown("---")
    st.caption("Shared demo profile · Asha Rao")
    if st.button("Reset local preview", use_container_width=True):
        st.session_state.workspace = seed_demo_state()
        st.session_state.pop("current_emergency_id", None)
        st.rerun()
    st.caption("Health readings and prescription files persist in the shared demo workspace. Other sections are local demo data.")

if st.session_state.large_text:
    st.markdown("<style>html{font-size:115%}p,label,button{font-size:1.03rem!important}</style>", unsafe_allow_html=True)


workspace = st.session_state.workspace
if cloud_client is not None and cloud_error is None:
    try:
        workspace["health"] = list_health_observations(cloud_client)
        workspace["prescriptions"] = list_prescription_records(cloud_client)
        cloud_active = True
    except Exception as exc:
        workspace["health"] = []
        workspace["prescriptions"] = []
        cloud_error = str(exc)
        cloud_active = False


if cloud_active:
    st.markdown(
        "<div class='vl-demo'><span class='vl-dot'></span><strong>SHARED DEMO STORAGE CONNECTED</strong><span>Records are visible to anyone using this public demo. Use fictional data only — never enter real health information.</span></div>",
        unsafe_allow_html=True,
    )
else:
    notice = cloud_error or "Database connection is unavailable."
    st.markdown(
        f"<div class='vl-demo'><span class='vl-dot'></span><strong>DEMO MODE</strong><span>Health and prescription data may not persist right now. {html_text(notice[:150])}</span></div>",
        unsafe_allow_html=True,
    )

hero_greeting = "Hi Asha, welcome back."
st.markdown(
    f"""
    <div class="vl-hero">
      <div><div class="kicker">INDIA-FIRST · ELDER-LED CARE</div><h1>{html_text(hero_greeting)}</h1><p>Your day, your routines and your people — in one calm place.</p></div>
      <div class="hero-mark">V</div>
    </div>
    """,
    unsafe_allow_html=True,
)

today = india_now().date()
today_reports = [r for r in workspace["dose_reports"] if r["reported_at"][:10] == today.isoformat()]
upcoming_appointments = [a for a in workspace["appointments"] if a["status"] == "Scheduled"]
upcoming_appointments.sort(key=lambda a: a["when"])
unresolved = active_emergency_events()
due_count = sum(1 for med in workspace["meds"] if med.get("active", True) and medication_state(med, workspace["dose_reports"]) in {"Due · awaiting report", "Overdue · unconfirmed"})

m1, m2, m3, m4 = st.columns(4)
m1.metric("Medicine reports today", f"{len(today_reports)} / {sum(1 for x in workspace['meds'] if x.get('active', True))}", help="Self-reported only; not proof of ingestion.")
m2.metric("Medicine reminders needing review", due_count)
m3.metric("Next appointment", fmt_datetime(upcoming_appointments[0]["when"]).split("·")[-1].strip() if upcoming_appointments else "None scheduled")
m4.metric("Open safety events", len(unresolved))

if section == "Home":
    with st.expander("Guided demo · follow one family care journey", expanded=False):
        st.caption("A short walkthrough for judges: record a routine, notice a change, coordinate support, test the safety flow, then prepare a care handoff.")
        g1, g2, g3 = st.columns(3)
        g1.button("1 · Medicine routine", use_container_width=True, on_click=navigate_to_section, args=("Medicines",))
        g2.button("2 · Health journal", use_container_width=True, on_click=navigate_to_section, args=("Health journal",))
        g3.button("3 · Family coordination", use_container_width=True, on_click=navigate_to_section, args=("Family circle",))
        g4, g5 = st.columns(2)
        g4.button("4 · Safety response", use_container_width=True, on_click=navigate_to_section, args=("Emergency centre",))
        g5.button("5 · Build Care Passport", use_container_width=True, on_click=navigate_to_section, args=("Care Passport",))
    st.subheader("Your care, at a glance")
    components.html(voice_companion_html(workspace["meds"], workspace["appointments"], VOICE_LANGUAGES[language_label]), height=75, scrolling=False)
    left, right = st.columns([1.25, 0.75], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**Today's medication routine**")
            for med in workspace["meds"]:
                if not med.get("active", True):
                    continue
                med_status = medication_state(med, workspace["dose_reports"])
                c1, c2, c3 = st.columns([2.2, 1, 1.2])
                c1.markdown(f"**{html_text(med['name'])}**  \n<span class='vl-small'>{html_text(med['strength'])} · {html_text(med['time'])}</span>", unsafe_allow_html=True)
                c2.markdown(f"{status_badge(med_status)} {med_status}")
                if med_status != "Reported today":
                    if c3.button("Report dose", key=f"home_report_{med['id']}"):
                        workspace["dose_reports"].append(record_dose(med["id"]))
                        add_event("Dose self-reported", f"{med['name']} · report entered by demo user")
                        st.rerun()
                else:
                    c3.caption("Recorded")
                st.divider()
            st.caption("A report records what the person says happened. It does not verify ingestion or change a prescription.")
        with st.container(border=True):
            st.markdown("**Family care plan · today**")
            todays_tasks = [task for task in workspace["tasks"] if datetime.fromisoformat(task["due"]).date() == today and task["status"] != "Completed"]
            if not todays_tasks:
                st.info("No family tasks are scheduled for today.")
            for task in todays_tasks:
                st.markdown(f"**{html_text(task['title'])}** · {html_text(task['assignee'])}  \n<span class='vl-small'>{fmt_datetime(task['due'])}</span>", unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown("**Daily wellbeing check-in**")
            st.caption("A simple routine check — not a clinical assessment.")
            with st.form("daily_checkin"):
                meals = st.selectbox("Meals", ["Not asked yet", "Had meals", "Needs help with meals"])
                hydration = st.selectbox("Water check-in", ["Not asked yet", "Had water", "Would like a reminder"])
                mood = st.selectbox("How are you feeling?", ["Not answered", "Doing okay", "Would like a family call", "Would like support"])
                note = st.text_input("Optional note")
                submitted = st.form_submit_button("Save check-in", type="primary", use_container_width=True)
            if submitted:
                workspace["checkins"].insert(0, {"at": india_now().isoformat(), "meals": meals, "hydration": hydration, "mood": mood, "note": note})
                add_event("Daily check-in completed", "A wellbeing check-in was recorded in the demo.")
                st.success("Check-in saved in this demo session.")
        with st.container(border=True):
            st.markdown("**Safety network**")
            st.markdown(f"<div class='vl-pill'>{len(workspace['contacts'])} trusted contacts in sample network</div>", unsafe_allow_html=True)
            st.write("Primary contact:", workspace["contacts"][0]["name"] if workspace["contacts"] else "Not configured")
            st.write("National emergency number in India: **112**")
            st.link_button("Open emergency centre", "https://112.gov.in/", use_container_width=True)
    with st.container(border=True):
        st.markdown("**Recent care activity**")
        for event in workspace["events"][:5]:
            st.markdown(f"**{html_text(event['title'])}**  \n<span class='vl-small'>{html_text(event['detail'])} · {fmt_datetime(event['at'])}</span>", unsafe_allow_html=True)

elif section == "Medicines":
    st.subheader("Medication journey")
    st.markdown("<div class='vl-muted'>Prescription record → daily routine → self-report → refill planning → professional review.</div>", unsafe_allow_html=True)
    left, right = st.columns([1.25, 0.75], gap="large")
    with left:
        for med in workspace["meds"]:
            with st.container(border=True):
                a, b = st.columns([2, 1])
                with a:
                    st.markdown(f"**{html_text(med['name'])}** · {html_text(med['strength'])}")
                    st.caption(f"Scheduled {med['time']} · {med['instructions']}")
                    state = medication_state(med, workspace["dose_reports"])
                    if med.get("active", True):
                        st.markdown(f"{status_badge(state)} **{state}**")
                    else:
                        st.markdown("• **Inactive record**")
                    if med["remaining_units"] <= 5 and med.get("active", True):
                        st.warning(f"Refill planning: approximately {med['remaining_units']} sample units recorded. Confirm actual supply before arranging a refill.")
                    else:
                        st.caption(f"Sample supply record: {med['remaining_units']} units · update manually.")
                with b:
                    if st.button("Report as taken", key=f"report_{med['id']}", disabled=state == "Reported today" or not med.get("active", True), use_container_width=True):
                        workspace["dose_reports"].append(record_dose(med["id"]))
                        add_event("Dose self-reported", f"{med['name']} · entered by demo user")
                        st.rerun()
                    if st.button("Mark inactive", key=f"inactive_{med['id']}", use_container_width=True, disabled=not med.get("active", True)):
                        med["active"] = False
                        add_event("Medicine record set inactive", f"{med['name']} · demo record only")
                        st.rerun()
        with st.container(border=True):
            st.markdown("**Dose report history**")
            if workspace["dose_reports"]:
                for report in sorted(workspace["dose_reports"], key=lambda x: x["reported_at"], reverse=True)[:10]:
                    med_name = next((x["name"] for x in workspace["meds"] if x["id"] == report["medication_id"]), "Medicine record")
                    st.write(f"✓ {med_name} · {fmt_datetime(report['reported_at'])} · Self-reported")
            else:
                st.caption("No sample dose reports yet.")
    with right:
        with st.container(border=True):
            st.markdown("**Add a sample medicine record**")
            with st.form("add_medicine"):
                name = st.text_input("Medicine label", placeholder="Medicine D")
                strength = st.text_input("Strength / label", placeholder="As written on the prescription")
                med_time = st.time_input("Reminder time", value=time(9, 0), step=timedelta(minutes=5))
                instructions = st.text_input("Routine note", placeholder="Example: after breakfast")
                stock = st.number_input("Approximate supply units", min_value=0, max_value=365, value=14)
                if st.form_submit_button("Add medicine record", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("Enter a medicine label.")
                    else:
                        workspace["meds"].append({"id": f"med-{len(workspace['meds'])+1}-{int(datetime.now().timestamp())}", "name": name.strip(), "strength": strength.strip() or "Not entered", "time": med_time.strftime("%H:%M"), "instructions": instructions.strip() or "No extra note", "remaining_units": int(stock), "active": True})
                        add_event("Medicine record added", f"{name.strip()} · sample record")
                        st.success("Sample record added.")
                        st.rerun()
        st.markdown("<div class='vl-note'>VayoLoop must never suggest a dose, change a prescription, or tell someone to stop a medicine. The product records the clinician-provided plan and flags possible conflicts for a qualified professional.</div>", unsafe_allow_html=True)

elif section == "Prescription library":
    st.subheader("Prescription library")
    st.caption(
        "Files persist in the shared public demo workspace. Anyone using this public app may view and change them."
        if cloud_active else
        "Cloud storage is currently unavailable; uploaded files will only be held in this temporary session."
    )
    st.markdown(
        "<div class='vl-note'>VayoLoop keeps the original document and its metadata. It does not run OCR, verify authenticity or decide whether a medicine is suitable for a condition. A doctor or pharmacist must review clinical questions. Do not use this hackathon prototype for real patient records.</div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown("**Add a prescription document**")
        with st.form("prescription_upload_form"):
            prescription_file = st.file_uploader(
                "Choose prescription file",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
                help="PDF or image, maximum 10 MB. The original file is kept for download during this session.",
            )
            document_label = st.text_input("Document label", placeholder="Prescription · November visit")
            prescribed_on = st.date_input("Prescription date", value=today)
            clinic = st.text_input("Clinic / hospital", placeholder="As printed on the document")
            clinician = st.text_input("Doctor / prescriber (optional)")
            condition_as_written = st.text_input("Condition / reason (only if written on the document)")
            prescription_notes = st.text_area("Notes for the care circle", placeholder="For example: bring the original to the next appointment")
            save_prescription = st.form_submit_button("Save prescription document", type="primary", use_container_width=True)
        if save_prescription:
            if prescription_file is None:
                st.error("Choose a PDF or image first.")
            else:
                file_bytes = prescription_file.getvalue()
                safe_name = prescription_file.name.replace("/", "_").replace(chr(92), "_").replace(chr(0), "")
                if len(file_bytes) > 10 * 1024 * 1024:
                    st.error("This file is larger than 10 MB. Choose a smaller copy.")
                elif cloud_active:
                    try:
                        saved_record = save_prescription_record(
                            cloud_client,
                            file_bytes,
                            prescription_file.name,
                            prescription_file.type or "",
                            document_label.strip() or safe_name,
                            prescribed_on.isoformat(),
                            clinic,
                            clinician,
                            condition_as_written,
                            prescription_notes,
                        )
                        workspace.setdefault("prescriptions", []).insert(0, saved_record)
                        add_event("Prescription document saved", safe_name)
                        st.success("Prescription and original file saved to the shared demo workspace. Anyone using this public app may view them.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Secure upload failed: {str(exc)[:180]}")
                else:
                    workspace.setdefault("prescriptions", []).insert(0, {
                        "id": f"rx-{int(datetime.now().timestamp() * 1000)}",
                        "document_label": document_label.strip() or safe_name,
                        "file_name": safe_name,
                        "file_type": prescription_file.type or "application/octet-stream",
                        "file_size_bytes": len(file_bytes),
                        "file_data_b64": base64.b64encode(file_bytes).decode("ascii"),
                        "prescribed_on": prescribed_on.isoformat(),
                        "clinic": clinic.strip(),
                        "clinician": clinician.strip(),
                        "condition_as_written": condition_as_written.strip(),
                        "notes": prescription_notes.strip(),
                        "uploaded_at": india_now().isoformat(),
                    })
                    add_event("Prescription document saved", safe_name)
                    st.success("Demo file added to this temporary session only. Shared cloud storage is unavailable.")
                    st.rerun()

    saved_prescriptions = workspace.setdefault("prescriptions", [])
    st.markdown(f"### Saved documents · {len(saved_prescriptions)}")
    if not saved_prescriptions:
        st.info("No prescription documents saved yet. Add a PDF or image above.")
    for prescription in saved_prescriptions:
        with st.container(border=True):
            st.markdown(f"**{html_text(prescription['document_label'])}**")
            detail_parts = [
                f"Date: {prescription.get('prescribed_on', 'Not recorded')}",
                f"File: {prescription.get('file_name', 'Document')}",
                f"Size: {prescription.get('file_size_bytes', 0) / 1024:.0f} KB",
            ]
            if prescription.get("clinic"):
                detail_parts.append(f"Clinic: {prescription['clinic']}")
            if prescription.get("clinician"):
                detail_parts.append(f"Prescriber: {prescription['clinician']}")
            st.caption(" · ".join(detail_parts))
            if prescription.get("condition_as_written"):
                st.write(f"Recorded reason: {prescription['condition_as_written']}")
            if prescription.get("notes"):
                st.write(prescription["notes"])
            d1, d2 = st.columns([1, 1])
            if prescription.get("is_cloud"):
                cache_key = f"vayoloop_rx_file_{prescription['id']}"
                if cache_key in st.session_state:
                    d1.download_button(
                        "Download demo file",
                        data=st.session_state[cache_key],
                        file_name=prescription["file_name"],
                        mime=prescription["file_type"],
                        key=f"rx_cloud_download_{prescription['id']}",
                        use_container_width=True,
                    )
                elif d1.button("Prepare demo download", key=f"rx_prepare_{prescription['id']}", use_container_width=True):
                    try:
                        st.session_state[cache_key] = download_prescription_file(
                            cloud_client, prescription["document_path"]
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Download failed: {str(exc)[:160]}")
            else:
                d1.download_button(
                    "Download demo file",
                    data=base64.b64decode(prescription["file_data_b64"]),
                    file_name=prescription["file_name"],
                    mime=prescription["file_type"],
                    key=f"rx_download_{prescription['id']}",
                    use_container_width=True,
                )

            remove_label = "Delete demo document" if prescription.get("is_cloud") else "Remove from this session"
            if d2.button(remove_label, key=f"rx_remove_{prescription['id']}", use_container_width=True):
                try:
                    if prescription.get("is_cloud"):
                        delete_prescription_record(
                            cloud_client, prescription["id"], prescription["document_path"]
                        )
                        st.session_state.pop(f"vayoloop_rx_file_{prescription['id']}", None)
                        st.success("Prescription record and original file deleted from the shared demo workspace.")
                    else:
                        st.success("Prescription removed from this demo session.")
                    workspace["prescriptions"] = [item for item in saved_prescriptions if item["id"] != prescription["id"]]
                    add_event("Prescription document removed", prescription["file_name"])
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not remove the document: {str(exc)[:180]}")

elif section == "Health journal":
    st.subheader("Health progress journal")
    st.caption(
        "Readings persist in the shared public demo workspace and are visible to anyone using this app."
        if cloud_active else
        "Cloud storage is unavailable; readings will only be held in this temporary session."
    )
    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**Recorded observations**")
            if not workspace["health"]:
                st.info("No readings have been recorded.")
            else:
                st.dataframe(
                    [
                        {
                            "Observation": item["metric"],
                            "Value": f"{item['value']} {item['unit']}",
                            "Recorded at": fmt_datetime(item["observed_at"]),
                            "Source": item["source"],
                        }
                        for item in sorted(workspace["health"], key=lambda x: x["observed_at"], reverse=True)
                    ],
                    hide_index=True,
                    use_container_width=True,
                    height=320,
                )
                st.caption(
                    f"{len(workspace['health'])} observations in the shared demo workspace."
                    if cloud_active else
                    f"{len(workspace['health'])} observations saved in this session."
                )
                export_col1, export_col2 = st.columns(2)
                export_col1.download_button(
                    "Download health history CSV",
                    data=health_records_csv(workspace["health"]),
                    file_name=f"vayoloop-health-history-{today.isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
                export_col2.download_button(
                    "Download health history JSON",
                    data=json.dumps(sorted(workspace["health"], key=lambda item: item["observed_at"]), ensure_ascii=False, indent=2),
                    file_name=f"vayoloop-health-history-{today.isoformat()}.json",
                    mime="application/json",
                    use_container_width=True,
                )
        with st.container(border=True):
            st.markdown("**Health trend analysis**")
            trend_summaries = analyse_health_trends(workspace["health"], now=india_now())
            if not trend_summaries:
                st.info("Add valid, dated numeric observations to build a trend.")
            else:
                labels = [
                    f"{item['metric']} · {item['unit'] or 'unit not set'}"
                    for item in trend_summaries
                ]
                selected_label = st.selectbox(
                    "Choose an observation to analyse",
                    labels,
                    key="health_trend_metric",
                )
                selected_trend = trend_summaries[labels.index(selected_label)]
                latest_col, change_col, window_col = st.columns(3)
                latest_col.metric(
                    "Latest recorded value",
                    f"{selected_trend['latest_value']:g} {selected_trend['unit']}".strip(),
                )
                if selected_trend["change_vs_previous"] is not None:
                    change_col.metric(
                        "Change vs previous",
                        f"{selected_trend['change_vs_previous']:+g} {selected_trend['unit']}".strip(),
                        delta_color="off",
                    )
                else:
                    change_col.metric("Change vs previous", "Need 2 records")
                if selected_trend["window_change"] is not None:
                    window_col.metric(
                        f"Average change · {selected_trend['window_size']} vs prior {selected_trend['window_size']}",
                        f"{selected_trend['window_change']:+.2f} {selected_trend['unit']}".strip(),
                        delta_color="off",
                    )
                else:
                    window_col.metric(
                        "Rolling comparison",
                        f"Need {selected_trend['window_size'] * 2} records",
                    )

                chart_points = [
                    {
                        "Recorded at": datetime.fromisoformat(item["observed_at"]),
                        "Value": item["value"],
                    }
                    for item in selected_trend["readings"]
                ]
                st.line_chart(
                    chart_points,
                    x="Recorded at",
                    y="Value",
                    height=230,
                    use_container_width=True,
                )
                st.caption(
                    f"{selected_trend['count']} records · {selected_trend['freshness']} · "
                    f"latest-vs-previous direction: {selected_trend['direction_vs_previous']}. "
                    "Direction describes the numbers only; it is not a medical assessment."
                )

                st.markdown("**Recorded trend summary**")
                summary_rows = []
                for item in trend_summaries:
                    latest_text = f"{item['latest_value']:g} {item['unit']}".strip()
                    if item["change_vs_previous"] is None:
                        change_text = "Need more records"
                    else:
                        change_text = f"{item['change_vs_previous']:+g} {item['unit']}".strip()
                    summary_rows.append({
                        "Observation": item["metric"],
                        "Latest": latest_text,
                        "Change vs previous": change_text,
                        "Records": item["count"],
                        "Data freshness": item["freshness"],
                    })
                st.dataframe(summary_rows, hide_index=True, use_container_width=True)
                st.caption(
                    "Rolling averages compare the latest 3 entries with the preceding 3 entries "
                    "for the same observation and unit. More history improves context; no universal "
                    "normal range or diagnosis is inferred."
                )
    with right:
        with st.container(border=True):
            st.markdown("**Add an observation**")
            with st.form("health_observation"):
                metric = st.selectbox("Observation", ["Daily steps", "Sleep duration", "Resting heart rate", "Blood pressure — systolic", "Blood pressure — diastolic", "Blood glucose", "Weight", "Other"])
                value = st.number_input("Recorded value", min_value=0.0, value=0.0, step=0.1, format="%.2f")
                unit_default = {"Daily steps":"steps","Sleep duration":"hours","Resting heart rate":"bpm","Blood pressure — systolic":"mmHg","Blood pressure — diastolic":"mmHg","Blood glucose":"mg/dL","Weight":"kg"}.get(metric, "")
                unit = st.text_input("Unit", value=unit_default, max_chars=32)
                source_options = (
                    ["Entered by family", "Entered by elder", "Wearable / device record", "Clinic report"]
                    if cloud_active else
                    ["Entered by family", "Entered by elder", "Compatible device (demo)", "Clinic report (demo)"]
                )
                source = st.selectbox("Source", source_options)
                reading_date = st.date_input("Reading date", value=today, key="health_reading_date")
                reading_time = st.time_input("Reading time", value=india_now().time().replace(second=0, microsecond=0), step=timedelta(minutes=5), key="health_reading_time")
                if st.form_submit_button("Save observation", type="primary", use_container_width=True):
                    observed_at = datetime.combine(reading_date, reading_time, tzinfo=INDIA_TZ).isoformat(timespec="seconds")
                    try:
                        if cloud_active:
                            save_health_observation(
                                cloud_client,
                                metric,
                                float(value),
                                unit,
                                observed_at,
                                source,
                            )
                            workspace["health"] = list_health_observations(cloud_client)
                            success_message = "Observation saved to the shared demo workspace. It is visible to anyone using this public app."
                        else:
                            workspace["health"].append({"id": f"health-{int(datetime.now().timestamp() * 1000)}", "metric": metric, "value": value, "unit": unit, "observed_at": observed_at, "source": source})
                            success_message = "Observation saved in this demo session only."
                        add_event("Health observation added", f"{metric} · {source}")
                        st.success(success_message)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Observation could not be saved: {str(exc)[:180]}")
        st.markdown("<div class='vl-note'>A change in a number is not automatically good or bad. VayoLoop shows the recorded values and encourages the family to discuss concerns with a qualified clinician.</div>", unsafe_allow_html=True)

elif section == "Appointments":
    st.subheader("Appointments and care visits")
    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**Upcoming and previous appointments**")
            rows = sorted(workspace["appointments"], key=lambda x: x["when"])
            for appt in rows:
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    c1.markdown(f"**{appt['title']}**")
                    c1.caption(f"{appt['provider']} · {fmt_datetime(appt['when'])}")
                    c2.markdown(f"<span class='vl-pill'>{appt['status']}</span>", unsafe_allow_html=True)
                    if appt["status"] == "Scheduled" and c2.button("Mark visited", key=f"visited_{appt['id']}"):
                        appt["status"] = "Completed"
                        add_event("Appointment marked completed", appt["title"])
                        st.rerun()
    with right:
        with st.container(border=True):
            st.markdown("**Plan a visit**")
            with st.form("new_appointment"):
                title = st.text_input("Visit / appointment", placeholder="Follow-up visit")
                provider = st.text_input("Doctor / clinic", placeholder="Clinic name")
                visit_date = st.date_input("Date", value=today + timedelta(days=2), min_value=today)
                visit_time = st.time_input("Time", value=time(10, 0), step=timedelta(minutes=5))
                note = st.text_input("Bring / remember", placeholder="Reports, prescription, questions")
                if st.form_submit_button("Add appointment", type="primary", use_container_width=True):
                    if not title.strip():
                        st.error("Enter an appointment name.")
                    else:
                        visit_at = datetime.combine(visit_date, visit_time, tzinfo=INDIA_TZ)
                        workspace["appointments"].append({"id": f"apt-{int(datetime.now().timestamp())}", "title": title.strip(), "provider": provider.strip() or "Not specified", "when": visit_at.isoformat(), "status": "Scheduled", "note": note.strip()})
                        add_event("Appointment added", title.strip())
                        st.success("Appointment added.")
                        st.rerun()
        st.markdown("<div class='vl-note'>Reminder alerts in this prototype work only while the app page remains open and browser audio is enabled. They are not a substitute for a confirmed appointment notification service.</div>", unsafe_allow_html=True)

elif section == "Family circle":
    st.subheader("Family circle and shared responsibilities")
    st.caption("The elder stays at the centre. Demo roles illustrate access scopes; they are not production security controls.")
    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**People in the care circle**")
            for member in workspace["members"]:
                c1, c2 = st.columns([2, 1])
                c1.markdown(f"**{member['name']}** · {member['relationship']}")
                c1.caption(f"Role: {member['role']} · {member['permission']}")
                c2.markdown(f"<span class='vl-pill'>{member['role']}</span>", unsafe_allow_html=True)
                st.divider()
        with st.container(border=True):
            st.markdown("**Family task calendar**")
            for task in sorted(workspace["tasks"], key=lambda x: x["due"]):
                c1, c2, c3 = st.columns([2, 1.3, 0.8])
                c1.write(task["title"])
                c2.caption(f"{task['assignee']} · {fmt_datetime(task['due'])}")
                if task["status"] != "Completed" and c3.button("Done", key=f"task_done_{task['id']}"):
                    task["status"] = "Completed"
                    add_event("Family care task completed", task["title"])
                    st.rerun()
                elif task["status"] == "Completed":
                    c3.caption("✓ Done")
    with right:
        with st.container(border=True):
            st.markdown("**Add a trusted contact**")
            with st.form("add_contact"):
                contact_name = st.text_input("Name")
                relationship = st.text_input("Relationship", placeholder="Daughter, son, neighbour...")
                priority = st.selectbox("Escalation order", ["Primary contact", "Backup contact", "Nearby helper"])
                if st.form_submit_button("Add to demo network", type="primary", use_container_width=True):
                    if not contact_name.strip():
                        st.error("Enter a name.")
                    else:
                        workspace["contacts"].append({"id": f"contact-{int(datetime.now().timestamp())}", "name": contact_name.strip(), "relationship": relationship.strip() or priority, "priority": {"Primary contact":1, "Backup contact":2, "Nearby helper":3}[priority]})
                        workspace["contacts"].sort(key=lambda x: x["priority"])
                        st.success("Contact added to the demo network.")
                        st.rerun()
        with st.container(border=True):
            st.markdown("**Plan a family task**")
            with st.form("family_task"):
                task_title = st.text_input("Task", placeholder="Call after dinner")
                assignee = st.selectbox("Assigned to", [c["name"] for c in workspace["contacts"]] or ["Unassigned"])
                task_date = st.date_input("Date", value=today)
                task_time = st.time_input("Time", value=time(19, 0), key="task_time")
                if st.form_submit_button("Add care task", use_container_width=True):
                    if task_title.strip():
                        when = datetime.combine(task_date, task_time, tzinfo=INDIA_TZ)
                        workspace["tasks"].append({"id": f"task-{int(datetime.now().timestamp())}", "title": task_title.strip(), "assignee": assignee, "due": when.isoformat(), "status": "Planned"})
                        add_event("Family task planned", task_title.strip())
                        st.success("Task added.")
                        st.rerun()
        st.markdown("<div class='vl-note'>An invitation or role preview in this demo does not grant real account access. Production sharing needs verified identity, elder consent, server-enforced permissions and revocation.</div>", unsafe_allow_html=True)

elif section == "Emergency centre":
    st.subheader("Emergency and family escalation centre")
    st.markdown("<div class='vl-note vl-danger'><strong>Demo safety notice:</strong> the buttons below simulate events and do not notify contacts, call 112, detect falls or dispatch help. For a real emergency in India, call <strong>112</strong> directly.</div>", unsafe_allow_html=True)
    a, b = st.columns([1, 1], gap="large")
    with a:
        with st.container(border=True):
            st.markdown("**Test the response workflow**")
            st.caption("Use these controls to demonstrate the product logic with fictional people.")
            if st.button("Simulate possible fall signal", use_container_width=True):
                event = create_emergency_event("Possible fall signal", workspace["contacts"])
                workspace["emergency_events"].insert(0, event)
                st.session_state.current_emergency_id = event["id"]
                add_event("Possible fall signal · demo", "A simulated event is waiting for confirmation.")
                st.rerun()
            if st.button("Manual SOS · simulate immediate family alert", type="primary", use_container_width=True):
                event = create_emergency_event("Manual SOS", workspace["contacts"])
                workspace["emergency_events"].insert(0, event)
                st.session_state.current_emergency_id = event["id"]
                add_event("Manual SOS · demo", "Immediate family escalation simulated; no messages were sent.")
                st.rerun()
            st.markdown("---")
            st.markdown("**India emergency access**")
            st.markdown("For a real emergency, use the national emergency number **112**. VayoLoop's demo cannot place calls or dispatch responders.")
            st.link_button("Open 112 emergency portal", "https://112.gov.in/", use_container_width=True)
            st.markdown("[Call 112 from a phone](tel:112)")
    with b:
        with st.container(border=True):
            st.markdown("**Configured escalation order**")
            for contact in sorted(workspace["contacts"], key=lambda x: x["priority"]):
                st.markdown(f"**{contact['priority']}. {html_text(contact['name'])}**  \n<span class='vl-small'>{html_text(contact['relationship'])}</span>", unsafe_allow_html=True)
            st.caption("Real alert delivery needs verified contact channels, consent, network checks and delivery receipts.")
    active = active_emergency_events()
    if active:
        st.markdown("### Active test event")
        event = active[0]
        with st.container(border=True):
            st.markdown(f"**{event['event_type']}** · {fmt_datetime(event['created_at'])}")
            st.markdown(f"<span class='vl-pill warn'>{event['status']}</span> <span class='vl-pill'>DEMO ONLY · NOT SENT</span>", unsafe_allow_html=True)
            if event["status"] == "Awaiting person confirmation":
                st.warning("A possible event needs a response. In a real deployment, the device signal alone must not be treated as a confirmed fall.")
                c1, c2 = st.columns(2)
                if c1.button("Person responds: I'm okay", type="primary", use_container_width=True):
                    updated = close_emergency_event(event, safe=True)
                    update_emergency_event(updated)
                    add_event("Safety check closed", "Person confirmed okay in the demo flow.")
                    st.rerun()
                if c2.button("No response · simulate escalation", use_container_width=True):
                    update_emergency_event(escalate_emergency(event))
                    add_event("Emergency escalation simulated", "Family contact alerts queued in demo only.")
                    st.rerun()
            else:
                if event.get("acknowledged_by"):
                    st.success(f"{event['acknowledged_by']} acknowledged this demo alert.")
                for contact_update in event["contact_updates"]:
                    c1, c2 = st.columns([2, 1])
                    c1.write(f"**{contact_update['name']}** · {contact_update['relationship']}")
                    c1.caption(contact_update["status"])
                    if contact_update["status"] != "Acknowledged in demo" and event["status"] != "Closed · demo resolved":
                        if c2.button("Acknowledge", key=f"ack_{event['id']}_{contact_update['contact_id']}"):
                            updated = acknowledge_emergency_contact(event, contact_update["contact_id"])
                            update_emergency_event(updated)
                            add_event("Family alert acknowledged · demo", f"{contact_update['name']} acknowledged.")
                            st.rerun()
                if st.button("Close emergency test", use_container_width=True):
                    update_emergency_event(close_emergency_event(event))
                    st.success("Demo event closed.")
                    st.rerun()
    else:
        st.info("No active emergency test event. Start a simulation above to walk through the response.")
    with st.expander("Emergency history"):
        if workspace["emergency_events"]:
            for event in workspace["emergency_events"]:
                st.write(f"{event['event_type']} · {event['status']} · {fmt_datetime(event['created_at'])}")
        else:
            st.caption("No emergency events recorded in this demo session.")
    st.markdown("<div class='vl-small'>Production requirements: consented watch/home integrations, reliable server-side monitoring, event verification, delivery acknowledgements, backup contact escalation, location permissions, abuse prevention, audit logs and independent emergency-service integration validation.</div>", unsafe_allow_html=True)

elif section == "Connected living":
    st.subheader("Connected living")
    st.caption("Designed for compatible wearables, phone health platforms and supported home sensors. Not every brand or appliance exposes an integration.")
    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**Connected device register**")
            for device in workspace["devices"]:
                c1, c2 = st.columns([2, 1])
                c1.markdown(f"**{device['name']}** · {device['kind']}")
                c1.caption(f"{device['provider']} · Last sync: {fmt_datetime(device['last_sync'])}")
                c2.markdown("<span class='vl-pill'>SIMULATED</span>", unsafe_allow_html=True)
                st.divider()
            if st.button("Simulate device sync", type="primary", use_container_width=True):
                stamp = india_now().isoformat()
                for device in workspace["devices"]:
                    device["last_sync"] = stamp
                    device["status"] = "Simulated"
                add_event("Device sync simulated", "Connected device sample timestamps updated.")
                st.success("Sample sync recorded. No physical device was contacted.")
                st.rerun()
            if st.button("Simulate home safety sensor event", use_container_width=True):
                event = create_emergency_event("Home sensor activity · simulated", workspace["contacts"])
                workspace["emergency_events"].insert(0, event)
                st.session_state.current_emergency_id = event["id"]
                add_event("Home sensor event · demo", "Sample event created for emergency workflow.")
                st.rerun()
    with right:
        with st.container(border=True):
            st.markdown("**Register a compatible device (demo)**")
            with st.form("register_device"):
                device_name = st.text_input("Device name")
                kind = st.selectbox("Device type", ["Smartwatch", "Phone health platform", "Motion sensor", "Door sensor", "Smoke detector", "Gas detector", "Smart speaker", "Other"])
                provider = st.text_input("Brand / platform")
                consent = st.checkbox("I have permission to include this device in the sample profile.")
                if st.form_submit_button("Add device record", type="primary", use_container_width=True):
                    if not device_name.strip() or not consent:
                        st.error("Enter a device name and confirm permission.")
                    else:
                        workspace["devices"].append({"id": f"dev-{int(datetime.now().timestamp())}", "name": device_name.strip(), "kind": kind, "provider": provider.strip() or "Not entered", "status": "Simulated", "last_sync": None})
                        add_event("Device record added", f"{device_name.strip()} · demo registry")
                        st.success("Device record added.")
                        st.rerun()
    st.markdown("<div class='vl-note'>Device readings must show their source, timestamp and freshness. A disconnected or stale device must never be presented as live. Physical monitoring and smart-home control require provider-specific APIs, permissions and fail-safe testing.</div>", unsafe_allow_html=True)

elif section == "Local support":
    st.subheader("Local care directory")
    st.caption("A family-maintained directory for the elder's actual local support network. The sample directory starts empty so we don't invent nearby clinics or contact details.")
    with st.container(border=True):
        st.markdown("**Add a trusted local resource**")
        with st.form("add_resource"):
            resource_type = st.selectbox("Resource type", ["Hospital", "Clinic", "Doctor", "Pharmacy", "Ambulance provider", "Home-care service", "Physiotherapist", "Other"])
            resource_name = st.text_input("Name")
            area = st.text_input("Area / address label")
            resource_phone = st.text_input("Phone (optional)")
            details = st.text_input("Useful details", placeholder="Opening hours, appointment note, access information")
            if st.form_submit_button("Save local resource", type="primary"):
                if not resource_name.strip():
                    st.error("Enter a resource name.")
                else:
                    workspace["resources"].append({"type": resource_type, "name": resource_name.strip(), "area": area.strip(), "phone": resource_phone.strip(), "details": details.strip()})
                    add_event("Local support resource added", resource_name.strip())
                    st.success("Resource saved in this demo session.")
                    st.rerun()
    if workspace["resources"]:
        for resource in workspace["resources"]:
            with st.container(border=True):
                st.markdown(f"**{resource['name']}** · {resource['type']}")
                st.caption(" · ".join(x for x in [resource["area"], resource["phone"], resource["details"]] if x))
    st.markdown("---")
    st.markdown("**Health information sharing, later**")
    st.markdown("<div class='vl-note'>VayoLoop can be designed for optional ABDM / ABHA compatibility. This demo does not connect to ABDM, request an ABHA number or exchange medical records. Any future record exchange must use the official consent process.</div>", unsafe_allow_html=True)
    st.markdown("For urgent help in India, call **112**. [Official emergency response portal](https://112.gov.in/).")

elif section == "Care Passport":
    st.subheader("Care Passport")
    st.caption(
        "Health observations and prescription records come from the shared public demo workspace; other sections remain synthetic demo data."
        if cloud_active else
        "A portable, date-stamped handoff view built from fictional, session-only demo data."
    )
    passport = build_care_passport(workspace, profile_name="Asha Rao")
    if cloud_active:
        passport["notice"] = (
            "Mixed hackathon handoff: health observations and prescription metadata are read from the shared "
            "public demo workspace. Anyone using the public app can see these entries. Other modules may contain "
            "fictional demo data. This is not a clinical record or diagnosis."
        )
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Active medicines", passport["counts"]["active_medicines"])
    p2.metric("Prescription files", passport["counts"]["prescription_documents"])
    p3.metric("Health observations", passport["counts"]["health_observations_included"])
    p4.metric("Appointments", passport["counts"]["appointments"])
    p5.metric("Trusted contacts", passport["counts"]["trusted_contacts"])

    with st.container(border=True):
        st.markdown("**Medication plan**")
        st.table([
            {"Medicine": item["name"], "Label": item["label"], "Time": item["scheduled_time"], "Status": item["status"], "Approx. units": item["approx_supply_units"]}
            for item in passport["medicines"]
        ] or [{"Medicine": "No medicine records"}])
        st.caption("A dose report is self-reported. It does not prove ingestion or authorise a prescription change.")

    with st.container(border=True):
        st.markdown("**Saved prescription documents**")
        if passport["prescriptions"]:
            st.table([
                {
                    "Document": item["document_label"],
                    "Date": item["prescribed_on"],
                    "Clinic": item["clinic"] or "Not entered",
                    "Prescriber": item["clinician"] or "Not entered",
                    "Original file": item["file_name"],
                    "Availability": "Download in Prescription library",
                }
                for item in passport["prescriptions"]
            ])
        else:
            st.caption("No prescription documents saved yet.")
        st.caption("The Care Passport includes document details, not the binary file. Open Prescription library to download the original upload.")

    with st.container(border=True):
        st.markdown("**Recent health observations**")
        st.table([
            {"Observation": item["metric"], "Value": f'{item["value"]} {item["unit"]}', "Observed": item["observed_at_display"], "Source": item["source"]}
            for item in passport["health_observations"][:8]
        ] or [{"Observation": "No observations recorded"}])
        st.markdown("**Recent dose reports**")
        st.table([
            {"Medicine": item["medicine"], "Reported at": item["reported_at_display"], "Record type": item["source"]}
            for item in passport["dose_reports"][:8]
        ] or [{"Medicine": "No dose reports recorded"}])

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("**Appointments and family tasks**")
            st.table([
                {"Visit": item["visit"], "When": item["when_display"], "Status": item["status"]}
                for item in passport["appointments"]
            ] or [{"Visit": "No appointments recorded"}])
            st.table([
                {"Task": item["task"], "Assigned to": item["assignee"], "Due": item["due_display"], "Status": item["status"]}
                for item in passport["family_tasks"]
            ] or [{"Task": "No family tasks recorded"}])
    with right:
        with st.container(border=True):
            st.markdown("**Trusted care circle**")
            st.table([
                {"Priority": item["priority"], "Name": item["name"], "Relationship": item["relationship"]}
                for item in passport["care_circle"]
            ] or [{"Name": "No trusted contacts recorded"}])
            checkin = passport["latest_wellbeing_checkin"]
            st.markdown("**Latest wellbeing check-in**")
            if checkin:
                st.write(f'Recorded {checkin["recorded_at_display"]}')
                st.write(f'Meals: {checkin["meals"]} · Water: {checkin["hydration"]} · Mood: {checkin["mood"]}')
                if checkin["note"]:
                    st.caption(checkin["note"])
            else:
                st.caption("No wellbeing check-in recorded yet.")
            st.markdown("**Connected device register**")
            st.table([
                {"Device": item["name"], "Type": item["kind"], "Status": item["status"], "Last sync": item["last_sync_display"]}
                for item in passport["connected_devices"]
            ] or [{"Device": "No devices registered"}])

    if passport["active_safety_events"]:
        st.warning(f'{len(passport["active_safety_events"])} open safety test event(s) are included. These are simulated and have not notified anyone.')
    st.markdown(
        "<div class='vl-note'>This export is a convenience summary, not a medical record. Bring the original prescription and verified reports to appointments. Only share care details with the elder's permission. No information is sent to a clinician or family member by downloading this file.</div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown("**Export this care handoff**")
        st.caption(f'Profile: Asha Rao · Generated {passport["profile"]["generated_at_display"]} · Asia/Kolkata')
        export_allowed = st.checkbox(
            "I understand this export contains care details and should only be shared with the elder's permission.",
            key="passport_export_consent",
        )
        html_export = render_care_passport_html(passport)
        json_export = json.dumps(passport, ensure_ascii=False, indent=2)
        file_date = india_now().date().isoformat()
        e1, e2 = st.columns(2)
        e1.download_button(
            "Download print-ready Care Passport",
            data=html_export,
            file_name=f"vayoloop-care-passport-{file_date}.html",
            mime="text/html",
            disabled=not export_allowed,
            type="primary",
            use_container_width=True,
        )
        e2.download_button(
            "Download JSON data backup",
            data=json_export,
            file_name=f"vayoloop-care-data-{file_date}.json",
            mime="application/json",
            disabled=not export_allowed,
            use_container_width=True,
        )
        st.caption("The HTML file can be opened in a browser and printed or saved as PDF. Both downloads are generated locally from this demo session.")

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#859087;font-size:11px;line-height:1.6'>VayoLoop · Care beyond reminders · Elder-led, consent-first care<br>Fictional sample data · Not a medical device or emergency service · No live integrations are connected</div>",
    unsafe_allow_html=True,
)

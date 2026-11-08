"""iPhone の Safari 向けの音声まわりの部品（読み上げ・連続再生・音声認識）と共通スタイル。

読み上げは端末内蔵の音声合成（Web Speech API の speechSynthesis）を使うため、音声ファイルも API キーも不要。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from string import Template
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from english_app.listening import Track

SLOW_RATE = 0.75
SPEAK_BUTTON_HEIGHT = 68
PLAYER_HEIGHT = 250
SPEECH_COMPONENT_DIR = Path(__file__).resolve().parents[2] / "components" / "speech_recognizer"

_speech_recognizer_component = components.declare_component("speech_recognizer", path=str(SPEECH_COMPONENT_DIR))

_BASE_STYLE = """
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 5rem; max-width: 720px; }
.stButton button, .stFormSubmitButton button { min-height: 48px; font-size: 1rem; }
</style>
"""

# iPhone の自動修正・自動大文字化で、聞き取れた英語が書き換わるのを防ぐ（R-10）
_INPUT_ASSIST_SCRIPT = """
<script>
(function () {
  if (window.__englishInputAssist) { return; }
  window.__englishInputAssist = true;
  function apply() {
    document.querySelectorAll('input[type="text"]').forEach(function (input) {
      input.setAttribute("autocorrect", "off");
      input.setAttribute("autocapitalize", "none");
      input.setAttribute("spellcheck", "false");
    });
  }
  apply();
  new MutationObserver(apply).observe(document.body, { childList: true, subtree: true });
})();
</script>
"""

_FRAME_STYLE = """
<style>
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif; color: #24292f; }
  .row { display: flex; gap: 8px; }
  button { flex: 1; min-height: 46px; font-size: 16px; border-radius: 10px; border: 1px solid #d0d7de;
           background: #f6f8fa; color: #24292f; -webkit-tap-highlight-color: transparent; }
  button.primary { background: #0969da; border-color: #0969da; color: #ffffff; }
  button:active { opacity: 0.7; }
  #status { font-size: 12px; color: #cf222e; min-height: 16px; margin-top: 4px; }
  .now { font-size: 18px; line-height: 1.5; min-height: 84px; padding: 10px 12px; margin-bottom: 8px;
         border-radius: 10px; background: #f6f8fa; }
  .meta { font-size: 13px; color: #57606a; margin-bottom: 8px; }
</style>
"""

_VOICE_SCRIPT = """
var SECOND_SPEAKER_PITCH = 0.8;
var MS_PER_CHARACTER = 110;
var WATCHDOG_MARGIN_MS = 4000;
var CANCEL_SETTLE_MS = 120;
var NOVELTY_VOICE_PREFIXES = ["Albert", "Bad News", "Bahh", "Bells", "Boing", "Bubbles", "Cellos",
  "Good News", "Jester", "Organ", "Superstar", "Trinoids", "Whisper", "Wobble", "Zarvox", "Junior",
  "Ralph", "Kathy", "Fred"];

function englishVoices() {
  if (!window.speechSynthesis) { return []; }
  var voices = window.speechSynthesis.getVoices().filter(function (voice) {
    var lang = (voice.lang || "").replace("_", "-").toLowerCase();
    var isNovelty = NOVELTY_VOICE_PREFIXES.some(function (prefix) { return voice.name.indexOf(prefix) === 0; });
    return lang.indexOf("en-us") === 0 && !isNovelty;
  });
  function rank(voice) { return /premium|enhanced|neural|natural/i.test(voice.name) ? 0 : 1; }
  return voices.sort(function (a, b) { return rank(a) - rank(b); });
}

function showStatus(message) {
  var status = document.getElementById("status");
  if (status) { status.textContent = message; }
}

function speakText(text, rate, voiceIndex, onDone) {
  if (!window.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
    showStatus("この端末は読み上げに対応していません");
    return false;
  }
  var utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = rate;
  var voices = englishVoices();
  if (voices.length > 0) {
    utterance.voice = voices[voiceIndex % voices.length];
    if (voiceIndex > 0 && voices.length === 1) { utterance.pitch = SECOND_SPEAKER_PITCH; }
  }
  if (onDone) {
    var finished = false;
    var finish = function () { if (!finished) { finished = true; onDone(); } };
    utterance.onend = finish;
    utterance.onerror = finish;
    // iOS では onend が届かないことがあるため、文の長さから見積もった時間で次へ進める
    setTimeout(finish, text.length * MS_PER_CHARACTER / rate + WATCHDOG_MARGIN_MS);
  }
  window.speechSynthesis.speak(utterance);
  return true;
}

// iOS の Safari は cancel() の直後に speak() すると無視されることがあるため、少し待ってから話す
function speakAfterCancel(callback) {
  var synth = window.speechSynthesis;
  if (synth && (synth.speaking || synth.pending)) {
    synth.cancel();
    setTimeout(callback, CANCEL_SETTLE_MS);
  } else {
    callback();
  }
}
"""

_SPEAK_BUTTON_TEMPLATE = Template(
    """<!doctype html>
<html><head><meta charset="utf-8">$frame_style</head>
<body>
<div class="row">
  <button class="primary" id="play" type="button">▶ 再生</button>
  <button id="slow" type="button">🐢 ゆっくり</button>
</div>
<div id="status"></div>
<script>
$voice_script
var TEXT = $text;
function play(rate) {
  speakAfterCancel(function () { speakText(TEXT, rate, 0, null); });
}
document.getElementById("play").addEventListener("click", function () { play(1.0); });
document.getElementById("slow").addEventListener("click", function () { play($slow_rate); });
</script>
</body></html>"""
)

_PLAYER_TEMPLATE = Template(
    """<!doctype html>
<html><head><meta charset="utf-8">$frame_style</head>
<body>
<div class="now" id="now"></div>
<div class="meta" id="count"></div>
<div class="row">
  <button id="prev" type="button">⏮ 前へ</button>
  <button class="primary" id="toggle" type="button">▶ 再生</button>
  <button id="next" type="button">次へ ⏭</button>
</div>
<div id="status"></div>
<script>
$voice_script
var TRACKS = $tracks;
var REPEAT = $repeat;
var PAUSE_MS = $pause_ms;
var RATE = $rate;
var KEEP_AWAKE = $keep_awake;
var index = 0;
var pass = 0;
var playing = false;
var timer = null;
var generation = 0;
var wakeLock = null;

function render() {
  document.getElementById("now").textContent = TRACKS[index].text;
  document.getElementById("count").textContent =
    (index + 1) + " / " + TRACKS.length + "　（" + (pass + 1) + " / " + REPEAT + " 回目）";
  document.getElementById("toggle").textContent = playing ? "⏸ 一時停止" : "▶ 再生";
}

function clearTimer() {
  if (timer !== null) { clearTimeout(timer); timer = null; }
}

function playCurrent() {
  if (!playing) { return; }
  var myGeneration = ++generation;
  render();
  var track = TRACKS[index];
  var started = speakText(track.text, RATE, track.voice, function () {
    if (!playing || myGeneration !== generation) { return; }
    timer = setTimeout(advance, PAUSE_MS);
  });
  if (!started) { stop(); }
}

function advance() {
  timer = null;
  pass += 1;
  if (pass < REPEAT) { playCurrent(); return; }
  pass = 0;
  if (index + 1 >= TRACKS.length) { finish(); return; }
  index += 1;
  playCurrent();
}

function start() {
  playing = true;
  showStatus("");
  requestWakeLock();
  playCurrent();
}

function stop() {
  playing = false;
  generation += 1;
  clearTimer();
  if (window.speechSynthesis) { window.speechSynthesis.cancel(); }
  releaseWakeLock();
  render();
}

function finish() {
  stop();
  index = 0;
  pass = 0;
  render();
  showStatus("最後まで再生しました");
}

function jump(delta) {
  var wasPlaying = playing;
  stop();
  index = Math.min(Math.max(index + delta, 0), TRACKS.length - 1);
  pass = 0;
  render();
  if (wasPlaying) { setTimeout(start, CANCEL_SETTLE_MS); }
}

function requestWakeLock() {
  if (!KEEP_AWAKE || !("wakeLock" in navigator)) { return; }
  navigator.wakeLock.request("screen").then(function (lock) { wakeLock = lock; }).catch(function () {
    showStatus("この端末では、再生中に画面をつけたままにできませんでした");
  });
}

function releaseWakeLock() {
  if (wakeLock !== null) { wakeLock.release().catch(function () {}); wakeLock = null; }
}

document.addEventListener("visibilitychange", function () {
  if (document.visibilityState === "visible" && playing) { requestWakeLock(); }
});
document.getElementById("toggle").addEventListener("click", function () { if (playing) { stop(); } else { start(); } });
document.getElementById("prev").addEventListener("click", function () { jump(-1); });
document.getElementById("next").addEventListener("click", function () { jump(1); });
render();
</script>
</body></html>"""
)


def to_js_literal(value: Any) -> str:
    """Python の値を <script> 内に安全に埋め込める JS リテラルにする。"""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def inject_base_style() -> None:
    st.html(_BASE_STYLE)
    st.html(_INPUT_ASSIST_SCRIPT, unsafe_allow_javascript=True)


def speak_button(text: str) -> None:
    html = _SPEAK_BUTTON_TEMPLATE.substitute(
        frame_style=_FRAME_STYLE,
        voice_script=_VOICE_SCRIPT,
        text=to_js_literal(text),
        slow_rate=to_js_literal(SLOW_RATE),
    )
    st.iframe(html, height=SPEAK_BUTTON_HEIGHT)


def listening_player(tracks: Sequence[Track], *, repeat: int, pause_ms: int, rate: float, keep_awake: bool) -> None:
    html = _PLAYER_TEMPLATE.substitute(
        frame_style=_FRAME_STYLE,
        voice_script=_VOICE_SCRIPT,
        tracks=to_js_literal([{"text": track.text, "voice": track.voice} for track in tracks]),
        repeat=to_js_literal(repeat),
        pause_ms=to_js_literal(pause_ms),
        rate=to_js_literal(rate),
        keep_awake=to_js_literal(keep_awake),
    )
    st.iframe(html, height=PLAYER_HEIGHT)


def speech_recognizer(key: str, label: str = "🎤 タップして英語で話す") -> dict[str, Any] | None:
    """Safari 標準の音声認識（無料）で文字起こしする。結果は {"transcript": ...} か {"error": ...}。"""
    value = _speech_recognizer_component(label=label, lang="en-US", key=key, default=None)
    return value if isinstance(value, dict) else None

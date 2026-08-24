"""ui/insight.py — การ์ด "วิเคราะห์ข้อมูลจากความถี่"

วาดผลที่ core/rules.evaluate() สรุปมาให้ ไม่มีตรรกะการตัดสินใจในไฟล์นี้เลย
(แยกส่วนคิดกับส่วนวาดออกจากกัน — ส่วนคิดจึงเขียน unit test ได้)
"""
import html

import streamlit as st

from ui import theme as T


def _esc(s: str) -> str:
    return html.escape(str(s))


def _findings_html(findings) -> str:
    out = ""
    for f in findings:
        c = T.level_color(f.level)
        detail = (f'<div class="sv-find-d">{_esc(f.detail)}</div>'
                  if f.detail else "")
        out += (f'<div class="sv-find"><i style="background:{c}"></i>'
                f'<div><div class="sv-find-t">{_esc(f.title)}</div>{detail}</div></div>')
    return out


def _actions_html(actions) -> str:
    return "".join(
        f'<div class="sv-act"><b>{i}</b><span>{_esc(a)}</span></div>'
        for i, a in enumerate(actions, 1))


def render(v):
    """v = core.rules.Verdict"""
    color, label, icon = T.LEVEL.get(v.level, T.LEVEL["info"])
    conf_color = T.OK if v.confidence >= 75 else (
        T.WARN if v.confidence >= 45 else T.DANGER)

    parts = [
        '<div class="sv-ins">',
        '<div class="sv-ins-top">',
        f'<span class="sv-ins-tag" style="color:{color};'
        f'background:{color}1a;border-color:{color}59">{icon} {label}</span>',
        '<div class="sv-conf">',
        '<div class="sv-conf-k">ความเชื่อมั่นของข้อมูล</div>',
        f'<div class="sv-conf-v" style="color:{conf_color}">{v.confidence}%</div>',
        f'<div class="sv-conf-track"><div class="sv-conf-fill" '
        f'style="width:{v.confidence}%;background:{conf_color}"></div></div>',
        '</div></div>',
        f'<div class="sv-ins-head" style="color:{color}">{_esc(v.headline)}</div>',
    ]
    if v.summary:
        parts.append(f'<div class="sv-ins-sum">{_esc(v.summary)}</div>')
    if v.findings:
        parts.append('<div class="sv-sec">รายละเอียดที่ตรวจพบ</div>')
        parts.append(_findings_html(v.findings))
    if v.actions:
        parts.append('<div class="sv-sec">สิ่งที่ควรทำต่อ</div>')
        parts.append(_actions_html(v.actions))
    if v.confidence_note:
        parts.append(f'<div class="sv-note">เกณฑ์ความเชื่อมั่นรอบนี้ถูกกำหนดโดย: '
                     f'{_esc(v.confidence_note)}</div>')
    parts.append('</div>')

    st.markdown("".join(parts), unsafe_allow_html=True)

"""GGF family palette/layout taken from Floyd Headliner and LTX Spokesman."""
CSS = """
body, .gradio-container { background: #07101f !important; color: #e8eef9 !important; }
.gradio-container { max-width: 1320px !important; padding: clamp(8px,2vw,20px) !important; }
.ggf-hero { background: linear-gradient(135deg,#0b1220,#172554); border: 1px solid #334a6b;
 border-radius: 18px; padding: 22px 28px; display: flex; align-items: center; gap: 24px; margin-bottom: 12px; }
.ggf-hero-copy { flex: 1; min-width: 0; }
.ggf-kicker { color: #f5b942; font-size: .78rem; font-weight: 800; letter-spacing: .14em; }
.ggf-hero h1 { color: #f5b942; margin: 7px 0; font: 800 clamp(1.8rem,3vw,2.6rem)/1.12 'Segoe UI',Arial,sans-serif; }
.ggf-hero p { color: #dbeafe; margin: 0 0 8px; }
.ggf-links { display: flex; flex-wrap: wrap; gap: 6px 18px; }
.ggf-hero a { color: #8fc2ff; font-weight: 700; }
.ggf-hero img { width: 88px; height: 88px; border-radius: 12px; }
#ggf-activity { background: #172842; border: 1px solid #45607f; border-left: 4px solid #f5b942;
 border-radius: 10px; padding: 9px 14px; min-height: 44px; }
#ggf-activity p { color: #e8eef9 !important; margin: 0; }
#ggf-tabs button[role=tab] { background: #172842 !important; color: #e8eef9 !important;
 border: 1px solid #45607f !important; border-radius: 8px; padding: 10px 18px; min-height: 44px; }
#ggf-tabs button[role=tab][aria-selected=true] { background: #f5b942 !important; color: #091425 !important; font-weight: 800; }
.gradio-container textarea, .gradio-container input[type=text], .gradio-container input[type=number],
.gradio-container input[type=password] { background: #091425 !important; color: #e8eef9 !important; font-size: 16px; }
.gradio-container .options { background: #111c2f !important; color: #e8eef9 !important; border-color: #45607f !important; }
.gradio-container .options .item { color: #e8eef9 !important; }
.gradio-container .options .item.active, .gradio-container .options .item:hover { background: #284365 !important; }
[data-testid=block-label], .gradio-container [data-testid=block-info] { color: #e8eef9 !important; background: #111c2f !important; }
.ggf-powered { color: #9db0cc; font-size: .85rem; text-align: center; }
#ggf-generate { background: #f5b942 !important; color: #091425 !important; font-weight: 800; }
.gradio-container button:focus-visible { outline: 2px solid #8fc2ff; outline-offset: 2px; }
.gradio-container .label-wrap, .gradio-container .label-wrap:hover,
.gradio-container .label-wrap:focus, .gradio-container .label-wrap:active {
 background: #172842 !important; color: #e8eef9 !important; border-color: #45607f !important; }
.gradio-container .label-wrap span, .gradio-container .label-wrap svg { color: #e8eef9 !important; }
.gradio-container ::selection { background: #f5b942 !important; color: #091425 !important; }
html.ggf-light body, html.ggf-light .gradio-container { background: #eef3f9 !important; color: #172842 !important; }
html.ggf-light .gradio-container { --body-text-color: #172842; --block-background-fill: #ffffff;
 --body-text-color-dark: #172842; --block-background-fill-dark: #ffffff;
 --block-label-text-color: #172842; --block-label-text-color-dark: #172842;
 --block-info-text-color: #405776; --block-info-text-color-dark: #405776;
 --block-title-text-color: #172842; --block-title-text-color-dark: #172842;
 --block-title-background-fill: #e4edf8; --block-title-background-fill-dark: #e4edf8;
 --checkbox-label-text-color: #172842; --checkbox-label-text-color-dark: #172842;
 --checkbox-label-background-fill: #ffffff; --checkbox-label-background-fill-dark: #ffffff;
 --checkbox-label-text-color-selected: #091425; --checkbox-label-text-color-selected-dark: #091425;
 --input-background-fill: #ffffff; --input-background-fill-dark: #ffffff; --input-text-color: #172842; }
html.ggf-light .gradio-container .label-wrap, html.ggf-light .gradio-container .label-wrap:hover,
html.ggf-light .gradio-container .label-wrap:focus, html.ggf-light .gradio-container .label-wrap:active {
 background: #e4edf8 !important; color: #172842 !important; border-color: #9db0cc !important; }
html.ggf-light .gradio-container .label-wrap span, html.ggf-light .gradio-container .label-wrap svg { color: #172842 !important; }
html.ggf-light .gradio-container .prose { color: #172842 !important; }
html.ggf-light .gradio-container textarea, html.ggf-light .gradio-container input[type=text],
html.ggf-light .gradio-container input[type=number], html.ggf-light .gradio-container input[type=password] { background: #ffffff !important; color: #172842 !important; }
html.ggf-light [data-testid=block-label], html.ggf-light .gradio-container [data-testid=block-info] { color: #172842 !important; background: #ffffff !important; }
html.ggf-light .gradio-container .options { background: #ffffff !important; color: #172842 !important; }
html.ggf-light .gradio-container .options .item { color: #172842 !important; }
html.ggf-light .gradio-container .options .item.active, html.ggf-light .gradio-container .options .item:hover { background: #dce7f5 !important; }
html.ggf-light .ggf-powered { color: #405776; }
@media(max-width:680px) {
 .ggf-hero { padding: 14px 16px; border-radius: 14px; gap: 10px; }
 .ggf-hero img { display: none; }
 .ggf-kicker { font-size: .68rem; letter-spacing: .1em; }
 .ggf-hero h1 { font-size: clamp(1.6rem,7vw,2rem); }
 .ggf-hero p { font-size: .9rem; }
 .ggf-links a { font-size: .82rem; }
 #ggf-tabs button[role=tab] { padding: 10px 16px; }
 #ggf-voice-row { flex-direction: column; }
 #ggf-voice-row > * { width: 100% !important; min-width: 0 !important; }
}
"""

LOAD_JS = """(token) => {
 const key='ggf-zonos-workspace';
 let saved=localStorage.getItem(key);
 if (!saved || !/^[0-9a-f]{32}$/.test(saved)) { saved=crypto.randomUUID().replaceAll('-',''); localStorage.setItem(key,saved); }
 document.documentElement.classList.toggle('ggf-light',localStorage.getItem('ggf-zonos-theme') !== 'dark');
 return saved;
}"""
APPEARANCE_JS = """(value) => {
 localStorage.setItem('ggf-zonos-theme',value);
 document.documentElement.classList.toggle('ggf-light',value==='light');
}"""

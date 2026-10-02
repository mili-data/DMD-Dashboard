from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


st.set_page_config(page_title="Biljettförsäljning", layout="wide")

HUVUDFARG = "#0B3C5D"
ACCENT = "#D9B310"
LJUS = "#328CC1"

st.markdown(
    f"""
    <style>
        .block-container {{ padding-top: 1.6rem; padding-bottom: 1rem; }}
        h1 {{ color: {HUVUDFARG}; margin-bottom: 0; }}
        [data-testid="stMetric"] {{
            background: #FFFFFF;
            border: 1px solid #E3EAEF;
            border-left: 5px solid {ACCENT};
            border-radius: 8px;
            padding: 12px 16px;
        }}
        [data-testid="stMetricLabel"] {{ color: #6B7A87; }}
        [data-testid="stMetricValue"] {{ color: {HUVUDFARG}; font-size: 1.7rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def las_biljetter():
    fil = Path(__file__).parent / "data" / "tickets.csv"
    return pd.read_csv(fil, na_values=["NULL", ""])


def tal(varde, enhet=""):
    return f"{varde:,.0f}".replace(",", " ") + enhet


biljetter = las_biljetter()
obligatoriska_kolumner = {
    "ticket_id",
    "match_id",
    "spectator_id",
    "ticket_class",
    "ticket_price",
    "purchase_date",
    "seat_number",
    "payment_method",
}
saknade_kolumner = obligatoriska_kolumner.difference(biljetter.columns)
if saknade_kolumner:
    st.error(f"CSV-filen saknar kolumner: {', '.join(sorted(saknade_kolumner))}")
    st.stop()

biljetter["purchase_date"] = pd.to_datetime(
    biljetter["purchase_date"], errors="coerce"
)
biljetter["ticket_price"] = pd.to_numeric(
    biljetter["ticket_price"], errors="coerce"
)
biljetter["ticket_class"] = biljetter["ticket_class"].fillna("Okänd")
biljetter["payment_method"] = biljetter["payment_method"].fillna("Okänd")
biljetter["month"] = biljetter["purchase_date"].dt.strftime("%Y-%m")

st.title("Biljettförsäljning")
st.caption("Översikt över biljettintäkter, försäljning och betalningsmetoder")

with st.sidebar:
    st.header("Filter")
    manader = sorted(biljetter["month"].dropna().unique().tolist())
    vald_manad = st.selectbox("Köpmånad", ["Alla"] + manader)

    klasser = sorted(biljetter["ticket_class"].unique().tolist())
    valda_klasser = st.multiselect("Biljettklass", klasser, default=klasser)

    betalmetoder = sorted(biljetter["payment_method"].unique().tolist())
    valda_betalmetoder = st.multiselect(
        "Betalningsmetod", betalmetoder, default=betalmetoder
    )

filtrerad = biljetter.copy()
if vald_manad != "Alla":
    filtrerad = filtrerad[filtrerad["month"] == vald_manad]
filtrerad = filtrerad[
    filtrerad["ticket_class"].isin(valda_klasser)
    & filtrerad["payment_method"].isin(valda_betalmetoder)
]

if filtrerad.empty:
    st.info("Inga biljetter matchar filtren.")
    st.stop()

pris = filtrerad["ticket_price"].fillna(0)
salda = int((pris > 0).sum())
aterbetalningar = int((pris < 0).sum())
nettointakt = pris.sum()
snittpris = pris[pris > 0].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Sålda biljetter", tal(salda))
k2.metric("Nettointäkt", tal(nettointakt, " kr"))
k3.metric("Snittpris", tal(snittpris, " kr") if pd.notna(snittpris) else "–")
k4.metric("Återbetalningar", tal(aterbetalningar))

manadsdata = (
    filtrerad.dropna(subset=["month"])
    .groupby("month", as_index=False)["ticket_price"]
    .sum()
)
klassdata = (
    filtrerad.groupby("ticket_class", as_index=False)["ticket_price"]
    .sum()
    .sort_values("ticket_price", ascending=False)
)
betaldata = (
    filtrerad[filtrerad["ticket_price"] > 0]
    .groupby("payment_method", as_index=False)["ticket_id"]
    .count()
    .rename(columns={"ticket_id": "antal_biljetter"})
    .sort_values("antal_biljetter", ascending=False)
)

grafhojd = 250
manadsgraf = (
    alt.Chart(manadsdata)
    .mark_line(color=LJUS, point=True, strokeWidth=3)
    .encode(
        x=alt.X("month:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ticket_price:Q", title="Nettointäkt (kr)"),
        tooltip=[
            alt.Tooltip("month:N", title="Månad"),
            alt.Tooltip("ticket_price:Q", title="Nettointäkt", format=",.0f"),
        ],
    )
    .properties(height=grafhojd)
)

klassgraf = (
    alt.Chart(klassdata)
    .mark_bar(color=HUVUDFARG, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("ticket_class:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ticket_price:Q", title="Nettointäkt (kr)"),
        tooltip=[
            "ticket_class",
            alt.Tooltip("ticket_price:Q", title="Nettointäkt", format=",.0f"),
        ],
    )
    .properties(height=grafhojd)
)

betalgraf = (
    alt.Chart(betaldata)
    .mark_bar(color=ACCENT, cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
    .encode(
        y=alt.Y("payment_method:N", sort="-x", title=None),
        x=alt.X("antal_biljetter:Q", title="Sålda biljetter"),
        tooltip=["payment_method", "antal_biljetter"],
    )
    .properties(height=grafhojd)
)

st.subheader("Försäljningsanalys")
st.markdown("**Nettointäkt per månad**")
st.altair_chart(manadsgraf, width="stretch")

vanster, hoger = st.columns(2)
with vanster:
    st.markdown("**Nettointäkt per biljettklass**")
    st.altair_chart(klassgraf, width="stretch")
with hoger:
    st.markdown("**Sålda biljetter per betalningsmetod**")
    st.altair_chart(betalgraf, width="stretch")

st.subheader("Biljetter")
visning = filtrerad.rename(
    columns={
        "ticket_id": "Biljett-ID",
        "match_id": "Match-ID",
        "spectator_id": "Åskådar-ID",
        "ticket_class": "Biljettklass",
        "ticket_price": "Pris (kr)",
        "purchase_date": "Köpdatum",
        "seat_number": "Sittplats",
        "payment_method": "Betalningsmetod",
    }
)
st.dataframe(
    visning[
        [
            "Biljett-ID",
            "Match-ID",
            "Åskådar-ID",
            "Biljettklass",
            "Pris (kr)",
            "Köpdatum",
            "Sittplats",
            "Betalningsmetod",
        ]
    ].sort_values("Köpdatum", ascending=False),
    hide_index=True,
    width="stretch",
)
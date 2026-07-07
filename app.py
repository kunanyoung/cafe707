# -*- coding: utf-8 -*-
"""
제주도 카페 상권 분석 · 지도 시각화 (Streamlit)
데이터: 제주카페.xlsx (소상공인시장진흥공단 상가업소 정보 — 카페 추출본)
실행:  streamlit run app.py
"""

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium

# ──────────────────────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="제주 카페 상권 분석", page_icon="☕", layout="wide")

DATA_FILE = "제주카페.xlsx"
CAFE_LABEL = "카페"            # 상권업종소분류명 기준
JEJU_CENTER = (33.38, 126.55)  # 지도 초기 중심 (제주도 중앙)


# ──────────────────────────────────────────────────────────────
# 데이터 로드 (캐시)
# ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="제주 카페 데이터를 불러오는 중...")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]  # 컬럼명 공백 정리
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]  # 자동 인덱스 컬럼 제거
    return df


@st.cache_data(show_spinner="카페 데이터를 정제하는 중...")
def load_cafes(path: str) -> pd.DataFrame:
    df = load_data(path)
    # 데이터가 카페 외 업종을 포함하는 경우에만 필터 (이미 카페 추출본이면 그대로 사용)
    if "상권업종소분류명" in df.columns and (df["상권업종소분류명"] != CAFE_LABEL).any():
        cafe = df[df["상권업종소분류명"] == CAFE_LABEL].copy()
    else:
        cafe = df.copy()

    # 좌표 정제: 숫자 변환 + 제주 영역 범위 필터
    cafe["경도"] = pd.to_numeric(cafe["경도"], errors="coerce")
    cafe["위도"] = pd.to_numeric(cafe["위도"], errors="coerce")
    cafe = cafe.dropna(subset=["경도", "위도"])
    cafe = cafe[
        cafe["경도"].between(126.0, 127.0) & cafe["위도"].between(33.0, 34.0)
    ]
    return cafe.reset_index(drop=True)


try:
    cafes = load_cafes(DATA_FILE)
except FileNotFoundError:
    st.error(f"데이터 파일을 찾을 수 없습니다: `{DATA_FILE}` (app.py와 같은 폴더에 두세요)")
    st.stop()


# ──────────────────────────────────────────────────────────────
# 사이드바 필터
# ──────────────────────────────────────────────────────────────
st.sidebar.header("🔎 필터")

sigungu_all = sorted(cafes["시군구명"].dropna().unique().tolist())
sel_sigungu = st.sidebar.multiselect("시군구", sigungu_all, default=sigungu_all)

df_f = cafes[cafes["시군구명"].isin(sel_sigungu)]

dong_all = sorted(df_f["행정동명"].dropna().unique().tolist())
sel_dong = st.sidebar.multiselect("행정동 (선택)", dong_all, default=[])
if sel_dong:
    df_f = df_f[df_f["행정동명"].isin(sel_dong)]

keyword = st.sidebar.text_input("상호명 검색", "")
if keyword:
    df_f = df_f[df_f["상호명"].astype(str).str.contains(keyword, case=False, na=False)]

map_type = st.sidebar.radio("지도 표시 방식", ["마커 클러스터", "히트맵"], index=0)
base_map = st.sidebar.selectbox(
    "지도 종류(한글)", ["VWorld 일반지도", "VWorld 위성지도", "OpenStreetMap"], index=0,
    help="VWorld는 국토지리정보원 한글 지도입니다.",
)
max_markers = st.sidebar.slider(
    "지도에 표시할 최대 개수", 100, 3000, 1500, step=100,
    help="점이 많으면 지도 렌더링이 느려질 수 있습니다.",
)

st.sidebar.caption(f"전체 카페 {len(cafes):,}개 중 **{len(df_f):,}개** 선택됨")


# ──────────────────────────────────────────────────────────────
# 헤더 & 핵심 지표
# ──────────────────────────────────────────────────────────────
st.title("☕ 제주도 카페 상권 분석")
st.caption("소상공인시장진흥공단 상가업소 데이터 기반 · 상권업종소분류 = '카페'")

c1, c2, c3, c4 = st.columns(4)
c1.metric("선택된 카페 수", f"{len(df_f):,}")
c2.metric("제주 전체 카페 수", f"{len(cafes):,}")
top_dong = df_f["행정동명"].value_counts()
c3.metric("카페 최다 행정동", top_dong.index[0] if len(top_dong) else "-",
          f"{int(top_dong.iloc[0]):,}개" if len(top_dong) else "")
c4.metric("행정동 수", f"{df_f['행정동명'].nunique():,}")

st.divider()

if df_f.empty:
    st.warning("조건에 맞는 카페가 없습니다. 필터를 조정해 주세요.")
    st.stop()


# ──────────────────────────────────────────────────────────────
# 탭 구성
# ──────────────────────────────────────────────────────────────
tab_map, tab_chart, tab_table = st.tabs(["🗺️ 지도", "📊 분석 차트", "📋 데이터 표"])

# ── 지도 ─────────────────────────────────────────────
with tab_map:
    st.subheader(f"카페 분포 지도 — {map_type}")

    df_map = df_f if len(df_f) <= max_markers else df_f.sample(max_markers, random_state=42)
    if len(df_f) > max_markers:
        st.info(f"성능을 위해 {len(df_f):,}개 중 {max_markers:,}개를 표본 추출해 표시합니다.")

    # 한글 지도 타일 설정
    if base_map.startswith("VWorld"):
        layer = "Satellite" if "위성" in base_map else "Base"
        ext = "jpeg" if layer == "Satellite" else "png"
        m = folium.Map(location=list(JEJU_CENTER), zoom_start=10, tiles=None)
        folium.TileLayer(
            tiles=f"https://xdworld.vworld.kr/2d/{layer}/service/{{z}}/{{x}}/{{y}}.{ext}",
            attr="VWorld (국토지리정보원)",
            name=base_map,
        ).add_to(m)
    else:  # OpenStreetMap — 한국 지명이 한글로 표시됨
        m = folium.Map(location=list(JEJU_CENTER), zoom_start=10, tiles="OpenStreetMap")

    if map_type == "마커 클러스터":
        cluster = MarkerCluster().add_to(m)
        for _, r in df_map.iterrows():
            popup = folium.Popup(
                f"<b>{r['상호명']}</b><br>{r.get('행정동명','')}"
                f"<br>{r.get('도로명주소', r.get('지번주소',''))}",
                max_width=250,
            )
            folium.Marker(
                location=[r["위도"], r["경도"]],
                popup=popup,
                tooltip=str(r["상호명"]),
                icon=folium.Icon(color="cadetblue", icon="coffee", prefix="fa"),
            ).add_to(cluster)
    else:  # 히트맵
        HeatMap(
            df_map[["위도", "경도"]].values.tolist(),
            radius=12, blur=15, min_opacity=0.3,
        ).add_to(m)

    st_folium(m, use_container_width=True, height=560, returned_objects=[])

# ── 차트 ─────────────────────────────────────────────
with tab_chart:
    left, right = st.columns(2)

    with left:
        st.markdown("**행정동별 카페 수 (상위 20)**")
        top20 = df_f["행정동명"].value_counts().head(20).sort_values()
        fig = px.bar(
            x=top20.values, y=top20.index, orientation="h",
            labels={"x": "카페 수", "y": "행정동"},
            color=top20.values, color_continuous_scale="Teal",
        )
        fig.update_layout(showlegend=False, coloraxis_showscale=False,
                          height=560, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("**시군구별 카페 비중**")
        sig = df_f["시군구명"].value_counts()
        fig2 = px.pie(values=sig.values, names=sig.index, hole=0.45,
                      color_discrete_sequence=px.colors.sequential.Teal)
        fig2.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("**층별 분포 (층정보)**")
        floor = pd.to_numeric(df_f["층정보"], errors="coerce").dropna().astype(int)
        floor = floor[floor.between(1, 20)].value_counts().sort_index()
        if len(floor):
            fig3 = px.bar(x=floor.index.astype(str), y=floor.values,
                          labels={"x": "층", "y": "카페 수"},
                          color_discrete_sequence=["#2a9d8f"])
            fig3.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.caption("층 정보가 없습니다.")

    st.markdown("**상호명에 자주 쓰이는 키워드 (상위 20)**")
    words = (
        df_f["상호명"].dropna().astype(str)
        .str.replace(r"[^가-힣A-Za-z0-9\s]", " ", regex=True)
        .str.split().explode()
    )
    words = words[words.str.len() >= 2]
    stop = {"카페", "커피", "coffee", "cafe", "제주", "the", "The"}
    words = words[~words.isin(stop)]
    kw = words.value_counts().head(20).sort_values()
    if len(kw):
        figk = px.bar(x=kw.values, y=kw.index, orientation="h",
                      labels={"x": "빈도", "y": "키워드"},
                      color_discrete_sequence=["#e76f51"])
        figk.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(figk, use_container_width=True)

# ── 표 ───────────────────────────────────────────────
with tab_table:
    st.subheader("카페 목록")
    show_cols = ["상호명", "시군구명", "행정동명", "도로명주소", "지번주소", "층정보", "위도", "경도"]
    show_cols = [c for c in show_cols if c in df_f.columns]
    st.dataframe(df_f[show_cols], use_container_width=True, height=520)

    csv = df_f[show_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ CSV 다운로드", csv,
                       file_name="제주_카페_필터결과.csv", mime="text/csv")

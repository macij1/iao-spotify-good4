# interface/ui.py
import time
import uuid

import pandas as pd
import streamlit as st

from emo_core import (
    EMOTION_ORDER,
    SESSION_KEY_SCORES,
    SESSION_KEY_LYRICS,
    generate_emotion_scores,
    load_versions,
    save_versions,
    render_emotion_chart,
    render_compare_scatter,
    render_result_card,
)


def render_analyze_tab() -> None:
    """Render the 'Analyze your lyrics' tab."""
    # Layout: left (lyrics input) / right (results + save)
    col_left, col_right = st.columns([1, 1])

    # ----- Left column: lyrics input -----
    with col_left:
        st.markdown(
            '<div class="section-title">'
            '<span class="icon">📝</span><span>Lyrics</span></div>',
            unsafe_allow_html=True,
        )

        input_mode = st.radio(
            "How do you want to provide the lyrics?",
            ["Type manually", "Upload file (.txt)"],
            horizontal=True,
        )

        lyrics: str = ""

        if input_mode == "Type manually":
            lyrics = st.text_area(
                "Lyrics input",
                height=320,
                placeholder="Type your song lyrics here...",
                label_visibility="collapsed",
                key="lyrics_manual",
            )
        else:
            uploaded_file = st.file_uploader(
                "Upload a plain-text (.txt) file with the lyrics",
                type=["txt"],
                key="lyrics_file_uploader",
            )

            if uploaded_file is not None:
                try:
                    file_text = uploaded_file.read().decode(
                        "utf-8",
                        errors="ignore",
                    )
                except Exception:
                    file_text = ""

                lyrics = st.text_area(
                    "Loaded lyrics",
                    value=file_text,
                    height=320,
                    label_visibility="collapsed",
                    key="lyrics_file",
                )
            else:
                st.info("Upload a file to view and edit the lyrics here.")
                lyrics = ""

        st.write("")
        run_button = st.button("✨ Analyze emotional profile")

    # ----- Right column: chart + result card + save version -----
    with col_right:
        st.markdown(
            '<div class="section-title">'
            '<span class="icon">📊</span><span>Emotional profile</span></div>',
            unsafe_allow_html=True,
        )

        chart_placeholder = st.empty()
        result_placeholder = st.empty()

        # Initial render (previous scores or zeros)
        current_scores = st.session_state[SESSION_KEY_SCORES]
        render_emotion_chart(current_scores, chart_placeholder)

        # Analysis logic
        if run_button:
            if lyrics.strip():
                with st.spinner("Analyzing lyrics..."):
                    old_scores = st.session_state[SESSION_KEY_SCORES]
                    new_scores = generate_emotion_scores(lyrics)

                    # Smooth animation between old and new values
                    steps = 25
                    for i in range(steps + 1):
                        t = i / steps
                        t_smooth = 1 - (1 - t) ** 3  # ease-out cubic

                        interpolated = {}
                        for emo in EMOTION_ORDER:
                            start = old_scores[emo]
                            end = new_scores[emo]
                            interpolated[emo] = start + (
                                end - start
                            ) * t_smooth

                        render_emotion_chart(interpolated, chart_placeholder)
                        time.sleep(0.01)

                    # Store new scores and lyrics in session
                    st.session_state[SESSION_KEY_SCORES] = new_scores
                    st.session_state[SESSION_KEY_LYRICS] = lyrics

                # Show result card
                top_emotion = max(new_scores, key=new_scores.get)
                top_score = new_scores[top_emotion]
                with result_placeholder:
                    render_result_card(top_emotion, top_score)
            else:
                st.warning(
                    "Please enter or upload some lyrics before running the analysis."
                )
                # If there are previous scores, keep showing the last result card
                if sum(current_scores.values()) > 0:
                    top_emotion = max(current_scores, key=current_scores.get)
                    with result_placeholder:
                        render_result_card(
                            top_emotion, current_scores[top_emotion]
                        )
        else:
            # No new analysis: show last result, if any
            if sum(current_scores.values()) > 0:
                top_emotion = max(current_scores, key=current_scores.get)
                with result_placeholder:
                    render_result_card(
                        top_emotion, current_scores[top_emotion]
                    )

        # ----- Save version section -----
        st.write("")
        st.markdown(
            '<div class="section-title small">'
            '<span class="icon">💾</span>'
            '<span>Save this version</span></div>',
            unsafe_allow_html=True,
        )

        versions_df = load_versions()
        default_title = f"Version {len(versions_df) + 1}"
        version_title = st.text_input(
            "Version name",
            value=default_title,
            key="version_title_input",
        )

        if st.button("Save current analysis as version"):
            lyrics_to_save = st.session_state[SESSION_KEY_LYRICS]
            scores_to_save = st.session_state[SESSION_KEY_SCORES]

            if not lyrics_to_save.strip() or sum(scores_to_save.values()) == 0:
                st.warning("Run an analysis first before saving a version.")
            else:
                new_row = {
                    "version_id": str(uuid.uuid4()),
                    "title": version_title,
                    "lyrics": lyrics_to_save,
                }
                for emo in EMOTION_ORDER:
                    new_row[emo] = float(scores_to_save.get(emo, 0.0))

                versions_df = pd.concat(
                    [versions_df, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                save_versions(versions_df)
                st.success(f"Saved version: {version_title}")


def render_compare_tab() -> None:
    """Render the 'Compare versions of lyrics' tab."""
    st.markdown(
        '<div class="section-title">'
        '<span class="icon">🔍</span>'
        '<span>Compare versions of lyrics</span></div>',
        unsafe_allow_html=True,
    )

    versions_df = load_versions()

    if versions_df.empty:
        st.info(
            "No saved versions yet. Analyze some lyrics and save "
            "the results as versions in the first tab."
        )
        return

    st.markdown(
        "Select **two or more** versions to compare "
        "their emotional profiles."
    )

    options = {
        f"{row['title']}": row["version_id"]
        for _, row in versions_df.iterrows()
    }

    selected_titles = st.multiselect(
        "Versions",
        options=list(options.keys()),
    )

    if len(selected_titles) < 2:
        st.warning("Select at least two versions to see the comparison.")
        return

    selected_ids = [options[t] for t in selected_titles]
    selected_df = versions_df[versions_df["version_id"].isin(selected_ids)]

    st.markdown("#### Emotion comparison (scatter plot)")
    render_compare_scatter(selected_df)

    st.markdown("#### Numeric comparison table")

    table_df = selected_df[["title"] + EMOTION_ORDER].copy()

    # Convert scores 0–1 to percentages with 1 decimal
    for emo in EMOTION_ORDER:
        table_df[emo] = (table_df[emo] * 100).round(1).astype(str) + " %"

    table_df = table_df.set_index("title").T

    st.dataframe(table_df)

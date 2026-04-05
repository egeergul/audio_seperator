from __future__ import annotations

import re
import string
from pathlib import Path

from .common import derive_run_name, validate_readable_file


def _normalize_display_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Name must be non-empty.")
    if any(char.isupper() for char in cleaned):
        return cleaned
    return string.capwords(cleaned)


def _format_hashtag(name: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]+", "", name)
    if not compact:
        raise ValueError(f"Hashtag could not be derived from: {name}")
    return compact


def build_video_texts_template(song_name: str, artist_name: str, language: str) -> str:
    song_display = _normalize_display_name(song_name)
    artist_display = _normalize_display_name(artist_name)
    song_lower = song_name.strip().lower()
    artist_lower = artist_name.strip().lower()
    song_tag = _format_hashtag(song_display)
    artist_tag = _format_hashtag(artist_display)

    templates = {
        "en": (
            "Title:\n"
            f"{artist_display} \u2013 {song_display} (Vocals Only / Acapella)\n"
            "\n"
            "Description:\n"
            f"{song_display} \u2013 {artist_display} (Vocals Only / Acapella)\n"
            "\n"
            f"Experience the isolated vocals from {song_display} by {artist_display}. "
            "This version highlights the raw vocal performance without the instrumental, "
            "letting you hear the harmonies, tone, and vocal details clearly.\n"
            "\n"
            "Perfect for singers, producers, remixers, and fans who want to study the vocals "
            "or enjoy the acapella version of the song.\n"
            "\n"
            "\U0001f3a7 Use headphones for the best listening experience.\n"
            "\n"
            "If you enjoy vocals only / acapella / karaoke content, make sure to like the "
            "video and subscribe for more uploads.\n"
            "\n"
            "Comment below which song you want to hear next!\n"
            "\n"
            f"#{artist_tag} #{song_tag} #Acapella #VocalsOnly #IsolatedVocals\n"
            "\n"
            "Tags:\n"
            f"{artist_lower} {song_lower} vocals, "
            f"{song_lower} {artist_lower} acapella, "
            f"{song_lower} {artist_lower} vocals only, "
            f"{artist_lower} {song_lower} isolated vocals, "
            f"{song_lower} acapella, "
            f"{artist_lower} acapella, "
            f"{song_lower} karaoke, "
            f"{song_lower} instrumental removed, "
            f"{artist_lower} vocals only, "
            f"{song_lower} studio vocals, "
            f"{artist_lower} {song_lower} vocal track, "
            f"{song_lower} vocals only\n"
            "\n"
            "Pin comment:\n"
            "\U0001f3a4 More vocals only & karaoke tracks coming soon!\n"
            "\n"
            "Which song should I upload next? \U0001f3b6\n"
        ),
        "tr": (
            "Title:\n"
            f"{artist_display} \u2013 {song_display} (Sadece Vokaller / Acapella)\n"
            "\n"
            "Description:\n"
            f"{song_display} \u2013 {artist_display} (Sadece Vokaller / Acapella)\n"
            "\n"
            f"{artist_display} taraf\u0131ndan seslendirilen {song_display} par\u00e7as\u0131n\u0131n "
            "izole vokallerini deneyimleyin. Bu s\u00fcr\u00fcm, enstr\u00fcmantal olmadan ham vokal "
            "performans\u0131n\u0131 \u00f6ne \u00e7\u0131kar\u0131r; armonileri, t\u0131n\u0131y\u0131 ve vokal ayr\u0131nt\u0131lar\u0131n\u0131 net "
            "\u015fekilde duyman\u0131z\u0131 sa\u011flar.\n"
            "\n"
            "Vokalleri incelemek veya \u015fark\u0131n\u0131n acapella versiyonunun keyfini \u00e7\u0131karmak "
            "isteyen \u015fark\u0131c\u0131lar, prod\u00fckt\u00f6rler, remiks\u00e7iler ve hayranlar i\u00e7in m\u00fckemmel.\n"
            "\n"
            "\U0001f3a7 En iyi dinleme deneyimi i\u00e7in kulakl\u0131k kullan\u0131n.\n"
            "\n"
            "Sadece vokal / acapella / karaoke i\u00e7eriklerini seviyorsan\u0131z, videoyu be\u011fenip "
            "daha fazla y\u00fckleme i\u00e7in abone olmay\u0131 unutmay\u0131n.\n"
            "\n"
            "Bir sonraki hangi \u015fark\u0131y\u0131 duymak istedi\u011finizi a\u015fa\u011f\u0131ya yorum olarak yaz\u0131n!\n"
            "\n"
            f"#{artist_tag} #{song_tag} #Acapella #VocalsOnly #IsolatedVocals\n"
            "\n"
            "Tags:\n"
            f"{artist_lower} {song_lower} vocals, "
            f"{song_lower} {artist_lower} acapella, "
            f"{song_lower} {artist_lower} vocals only, "
            f"{artist_lower} {song_lower} isolated vocals, "
            f"{song_lower} acapella, "
            f"{artist_lower} acapella, "
            f"{song_lower} karaoke, "
            f"{song_lower} instrumental removed, "
            f"{artist_lower} vocals only, "
            f"{song_lower} studio vocals, "
            f"{artist_lower} {song_lower} vocal track, "
            f"{song_lower} vocals only\n"
            "\n"
            "Pin comment:\n"
            "\U0001f3a4 Yak\u0131nda daha fazla sadece vokal & karaoke par\u00e7as\u0131 geliyor!\n"
            "\n"
            "Bir sonraki hangi \u015fark\u0131y\u0131 y\u00fcklememi istersiniz? \U0001f3b6\n"
        ),
    }

    key = language.strip().lower()
    template = templates.get(key, templates["en"])
    return template


def find_vocals_audio_in_folder(folder_path: Path) -> Path:
    resolved = folder_path.expanduser().resolve()
    run_name = derive_run_name(resolved)
    expected = resolved / f"{run_name}_vocals.mp3"
    if expected.is_file():
        return expected

    matches = sorted(resolved.glob("*_vocals.mp3"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(
            "Could not find a vocals file. Expected "
            f"{expected.name} or a single '*_vocals.mp3' in {resolved}."
        )
    raise ValueError(
        "Multiple vocals files found. Provide a folder with a single '*_vocals.mp3'."
    )


def create_video_metadata_for_vocals(
    vocals_audio_path: Path,
    song_name: str,
    artist_name: str,
    language: str,
    output_text_path: Path | None = None,
) -> Path:
    validated_audio = validate_readable_file(vocals_audio_path)
    output_path = (
        output_text_path.expanduser().resolve()
        if output_text_path is not None
        else validated_audio.with_name(f"{validated_audio.stem}_video_texts.txt")
    )
    if output_path.exists():
        raise FileExistsError(f"Output text file already exists: {output_path}")

    content = build_video_texts_template(song_name, artist_name, language)
    output_path.write_text(content, encoding="utf-8")
    return output_path.resolve()

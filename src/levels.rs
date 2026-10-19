//! The tales you can choose from: each has its own story file and its own opening.

use std::sync::Arc;

use bevy::prelude::*;

use crate::intro::{Glow, IntroDef, Life, Runner, Wisps};
use crate::story::Story;

pub struct Level {
    /// Shown on the menu, e.g. "I".
    pub numeral: &'static str,
    pub card: &'static str,
    pub story: Arc<Story>,
    pub intro: IntroDef,
    /// Locked until then: Unix time in seconds, and how to say it on the menu.
    pub release: Option<(u64, &'static str)>,
}

impl Level {
    /// Whether it can be played yet. `unlocked` is the secret testing override.
    pub fn playable(&self, unlocked: bool) -> bool {
        unlocked || self.release.is_none_or(|(at, _)| now() >= at)
    }
}

/// Seconds since the Unix epoch, natively and in the browser.
fn now() -> u64 {
    web_time::SystemTime::now().duration_since(web_time::UNIX_EPOCH).map_or(0, |d| d.as_secs())
}

#[derive(Resource)]
pub struct Levels(pub Vec<Level>);

/// The tale being played (or last chosen on the menu).
#[derive(Resource, Default)]
pub struct CurrentLevel(pub usize);

impl Levels {
    /// Every level, with its story parsed. A broken story file is reported and ends the game.
    pub fn load() -> Result<Levels, String> {
        let parse = |file: &str, src: &str| Story::parse(src).map(Arc::new).map_err(|e| format!("{file}: {e}"));
        Ok(Levels(vec![
            Level {
                numeral: "I",
                card: "cards/fire.png",
                story: parse("story.txt", include_str!("../assets/story.txt"))?,
                intro: FIRE_INTRO,
                release: None,
            },
            Level {
                numeral: "II",
                card: "cards/sauna.png",
                story: parse("sauna.txt", include_str!("../assets/sauna.txt"))?,
                intro: SAUNA_INTRO,
                // 6 am Pacific time.
                release: Some((1_793_451_600, "Releasing October 31, 2026 · 6 AM PT")),
            },
            Level {
                numeral: "III",
                card: "cards/fox.png",
                story: parse("fox.txt", include_str!("../assets/fox.txt"))?,
                intro: FOX_INTRO,
                // 6 am Pacific time.
                release: Some((1_793_973_600, "Releasing November 6, 2026 · 6 AM PT")),
            },
        ]))
    }
}

// Timelines in seconds, matched to the intro music (INTRO_* and SAUNA_* in
// tools/make_audio.py). Positions in the paintings match tools/make_art.py.

/// Night over the village, the last ember dying, the view tilting up to the northern lights.
const FIRE_INTRO: IntroDef = IntroDef {
    painting: "intro/night.png",
    painting_aspect: 1440.0 / 1280.0,
    pan: &[(0.0, 0.0), (19.0, 0.06), (27.2, 1.0)],
    sideways: false,
    zoom: &[],
    glows: &[Glow {
        image: "intro/ember.png",
        center: Vec2::new(160.0 / 320.0, 342.0 / 360.0),
        width: 0.09,
        aspect: 1.0,
        life: Life::Dies(16.0),
    }],
    wisps: &[],
    runners: &[],
    captions: &[
        (2.6, 8.4, "Häme, long ago, in the time of the old words…"),
        (9.2, 14.6, "Every hearth kept a fire that had never once gone out."),
        (15.6, 20.6, "Until one night, one did."),
    ],
    hit: 28.0,
    prompt: 33.0,
    music: "music/intro.ogg",
    music_tail: "music/intro_tail.ogg",
    music_length: 54.0,
    title_loop: "music/title.ogg",
    title: "intro/title.png",
    flash: [1.0, 0.94, 0.78],
};

/// Dusk: down from the first stars to a sauna on the lake shore. Its window glows, then
/// gutters out, and two eyes open in the dark.
const SAUNA_INTRO: IntroDef = IntroDef {
    painting: "intro/dusk.png",
    painting_aspect: 1440.0 / 1280.0,
    pan: &[(0.0, 1.0), (3.0, 0.985), (15.0, 0.0)],
    sideways: false,
    zoom: &[],
    glows: &[
        Glow {
            image: "intro/window.png",
            center: Vec2::new(205.0 / 320.0, 322.0 / 360.0),
            width: 0.11,
            aspect: 1.0,
            life: Life::Dies(21.0),
        },
        Glow {
            image: "intro/eyes.png",
            center: Vec2::new(205.0 / 320.0, 322.0 / 360.0),
            width: 0.034,
            aspect: 0.4,
            life: Life::Opens(26.2),
        },
    ],
    wisps: &[Wisps {
        image: "effects/smoke.png",
        origin: Vec2::new(183.0 / 320.0, 306.0 / 360.0),
        width: 0.022,
        count: 10,
        life: 8.0,
        rise: 0.15,
        lean: 0.06,
        color: [0.38, 0.28, 0.32, 0.9],
    }],
    runners: &[],
    captions: &[
        (3.4, 8.6, "Every sauna has a keeper, living under the benches."),
        (9.4, 14.8, "In the sauna, you behave as you would in church."),
        (15.8, 20.4, "But one Saturday, somebody forgot."),
    ],
    hit: 28.0,
    prompt: 33.0,
    music: "music/intro_sauna.ogg",
    music_tail: "music/intro_sauna_tail.ogg",
    music_length: 52.0,
    title_loop: "music/title_sauna.ogg",
    title: "intro/title_sauna.png",
    flash: [1.0, 0.8, 0.58],
};

/// The polar night: down from a sky ablaze with the fox's fire to the fells and a herders'
/// camp. The lights die away, and in the dark a single spark glimmers in the snow.
const FOX_INTRO: IntroDef = IntroDef {
    painting: "intro/fells.png",
    painting_aspect: FOX_PANORAMA.1 / FOX_PANORAMA.0,
    // Start close on the blazing sky over the fells, then sweep across to the camp.
    pan: &[(0.0, 0.0), (2.5, 0.0), (23.0, 1.0)],
    sideways: true,
    zoom: &[(0.0, 1.3), (6.0, 1.18), (23.0, 1.0)],
    glows: &[
        Glow {
            image: "intro/aurora.png",
            center: Vec2::new(0.5, 60.0 / FOX_PANORAMA.1),
            width: 1.0,
            aspect: 120.0 / FOX_PANORAMA.0,
            life: Life::Dies(17.0),
        },
        Glow {
            image: "intro/spark.png",
            center: Vec2::new(FOX_SPARK.0 / FOX_PANORAMA.0, FOX_SPARK.1 / FOX_PANORAMA.1),
            width: 12.0 / FOX_PANORAMA.0,
            aspect: 1.0,
            life: Life::Opens(26.2),
        },
    ],
    wisps: &[Wisps {
        image: "effects/smoke.png",
        origin: Vec2::new(756.0 / FOX_PANORAMA.0, 106.0 / FOX_PANORAMA.1),
        width: 0.008,
        count: 10,
        life: 8.0,
        rise: 0.05,
        lean: 0.02,
        color: [0.34, 0.38, 0.5, 0.85],
    }],
    // The fox bounds along the ridge, then leaps up and runs off into the sky along its
    // trail of sparks, gone as the lights die.
    runners: &[Runner {
        frames: &["intro/fox_run_0.png", "intro/fox_run_1.png", "intro/fox_run_2.png", "intro/fox_run_3.png"],
        fps: 10.0,
        width: 46.0 / FOX_PANORAMA.0,
        aspect: 0.5,
        path: &[
            (0.6, 70.0 / FOX_PANORAMA.0, 116.0 / FOX_PANORAMA.1),
            (2.6, 120.0 / FOX_PANORAMA.0, 106.0 / FOX_PANORAMA.1),
            (4.4, 166.0 / FOX_PANORAMA.0, 100.0 / FOX_PANORAMA.1),
            (6.0, 196.0 / FOX_PANORAMA.0, 70.0 / FOX_PANORAMA.1),
            (8.0, 250.0 / FOX_PANORAMA.0, 44.0 / FOX_PANORAMA.1),
            (11.0, 360.0 / FOX_PANORAMA.0, 30.0 / FOX_PANORAMA.1),
            (15.0, 520.0 / FOX_PANORAMA.0, 28.0 / FOX_PANORAMA.1),
        ],
    }],
    captions: &[
        (3.4, 8.6, "In the north, in the long night, the sky was never dark."),
        (9.4, 14.8, "A fox ran across the fells, and its tail set the snow alight."),
        (15.8, 20.4, "Then one night, the fox stopped running."),
    ],
    hit: 28.0,
    prompt: 33.0,
    music: "music/intro_fox.ogg",
    music_tail: "music/intro_fox_tail.ogg",
    music_length: 52.0,
    title_loop: "music/title_fox.ogg",
    title: "intro/title_fox.png",
    flash: [0.78, 1.0, 0.88],
};

/// The intro panorama's size, and the place in it where the fox's last spark glimmers, in
/// room units, matching INTRO_SIZE and FOX_SPARK in tools/make_fox_art.py.
const FOX_PANORAMA: (f32, f32) = (832.0, 180.0);
const FOX_SPARK: (f32, f32) = (586.0, 171.0);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unreleased_tales_are_locked_unless_unlocked() {
        let levels = Levels::load().unwrap();
        let mut sauna = levels.0.into_iter().nth(1).unwrap();
        sauna.release = Some((now() + 3600, "in an hour"));
        assert!(!sauna.playable(false));
        assert!(sauna.playable(true), "the secret unlocks it for testing");
        sauna.release = Some((now() - 1, "a moment ago"));
        assert!(sauna.playable(false), "released tales open by themselves");
    }
}

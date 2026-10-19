//! The tales you can choose from: each has its own story file and its own opening.

use std::sync::Arc;

use bevy::prelude::*;

use crate::intro::{Glow, IntroDef, Life, Wisps};
use crate::story::Story;

pub struct Level {
    /// Shown on the menu, e.g. "I".
    pub numeral: &'static str,
    pub card: &'static str,
    pub story: Arc<Story>,
    pub intro: IntroDef,
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
            },
            Level {
                numeral: "II",
                card: "cards/sauna.png",
                story: parse("sauna.txt", include_str!("../assets/sauna.txt"))?,
                intro: SAUNA_INTRO,
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
    glows: &[Glow {
        image: "intro/ember.png",
        center: Vec2::new(160.0 / 320.0, 342.0 / 360.0),
        width: 0.09,
        aspect: 1.0,
        life: Life::Dies(16.0),
    }],
    wisps: &[],
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

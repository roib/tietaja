//! A level's opening: a tall painting the camera pans across, glowing lights that live and
//! die on cue, smoke rising, captions, and the title landing on the music's big hit. Click
//! to skip ahead to the title, and click again to start the level.
//!
//! What happens when is described by an [`IntroDef`] (see `levels.rs`), timed to that
//! level's intro music in tools/make_audio.py.

use bevy::{
    audio::{AudioSinkPlayback, Volume},
    prelude::*,
};

use crate::SoundOn;
use crate::levels::{CurrentLevel, Levels};

#[derive(States, Default, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Screen {
    /// Choosing a tale.
    #[default]
    Menu,
    Intro,
    Playing,
}

/// One level's opening sequence.
pub struct IntroDef {
    pub painting: &'static str,
    /// The painting's height over its width.
    pub painting_aspect: f32,
    /// Where the camera looks over time: (seconds, how far up the painting), where 0 shows
    /// its bottom and 1 its top. The camera eases between these.
    pub pan: &'static [(f32, f32)],
    pub glows: &'static [Glow],
    pub wisps: &'static [Wisps],
    pub captions: &'static [(f32, f32, &'static str)],
    /// When the title lands.
    pub hit: f32,
    /// When "Click to begin" appears.
    pub prompt: f32,
    pub music: &'static str,
    /// The music from `skip_lead` seconds before the hit, for skipping ahead.
    pub music_tail: &'static str,
    pub music_length: f32,
    /// A quiet loop for the title once the music ends.
    pub title_loop: &'static str,
    pub title: &'static str,
    /// The colour of the flash as the title lands.
    pub flash: [f32; 3],
}

/// Skipping lands this long before the hit, where the music's tail file begins.
pub const SKIP_LEAD: f32 = 0.6;

/// A light painted over the picture: an ember, a lit window, eyes in the dark.
pub struct Glow {
    pub image: &'static str,
    /// Its centre, as fractions of the painting's width and height.
    pub center: Vec2,
    /// Its width, as a fraction of the painting's width, and its height over its width.
    pub width: f32,
    pub aspect: f32,
    pub life: Life,
}

pub enum Life {
    /// Flickers from the start, flares once, and dies at this time.
    Dies(f32),
    /// Dark until this time, then opens like a pair of eyes, and blinks now and then.
    Opens(f32),
}

/// Smoke or steam rising from a point in the painting: puffs that drift up, swell and fade.
pub struct Wisps {
    pub image: &'static str,
    pub origin: Vec2,
    /// A puff's starting width, as a fraction of the painting's width.
    pub width: f32,
    pub count: usize,
    /// Seconds each puff lives, and how far it rises and leans (fractions of the width).
    pub life: f32,
    pub rise: f32,
    pub lean: f32,
    pub color: [f32; 4],
}

/// The intro is shown in a 16:9 frame, as large as fits the window.
pub const FRAME_ASPECT: f32 = 16.0 / 9.0;
const TITLE_ASPECT: f32 = 1600.0 / 520.0;
const INTRO_VOLUME: f32 = 0.85;
const LEAVE_SECONDS: f32 = 1.2;

#[derive(Resource, Default)]
struct Intro {
    /// Which level's opening this is.
    level: usize,
    /// Position in the timeline, kept in step with the music.
    time: f32,
    /// How long we've waited for the music to start (it may still be loading).
    waited: f32,
    /// Where in the timeline the playing music file begins (non-zero after skipping).
    music_offset: f32,
    /// The music's last reported position; it only updates every half second or so.
    last_position: f32,
    /// Seconds since the player chose to start the game.
    leaving: Option<f32>,
    /// When the quiet title-screen loop started, if it has.
    title_loop: Option<f32>,
}

#[derive(Component)]
struct IntroRoot;

#[derive(Component)]
struct IntroFrame;

#[derive(Component)]
struct Painting;

#[derive(Component)]
struct GlowLight(usize);

#[derive(Component)]
struct Puff {
    wisps: usize,
    /// Where in its life this puff is, as a fraction, at time zero.
    phase: f32,
}

#[derive(Component)]
struct Caption;

#[derive(Component)]
struct Title;

#[derive(Component)]
struct Prompt;

#[derive(Component)]
struct Fade;

#[derive(Component)]
struct Flash;

#[derive(Component)]
struct IntroMusic;

#[derive(Component)]
struct TitleMusic;

pub struct IntroPlugin;

impl Plugin for IntroPlugin {
    fn build(&self, app: &mut App) {
        app.init_state::<Screen>()
            .add_systems(OnEnter(Screen::Intro), spawn_intro)
            .add_systems(Update, (advance, input, animate).chain().run_if(in_state(Screen::Intro)))
            .add_systems(OnExit(Screen::Intro), despawn_intro);
    }
}

fn spawn_intro(mut commands: Commands, assets: Res<AssetServer>, sound: Res<SoundOn>, levels: Res<Levels>, level: Res<CurrentLevel>) {
    commands.insert_resource(Intro { level: level.0, ..default() });
    let def = &levels.0[level.0].intro;
    let clear = Color::NONE;
    let painting = commands
        .spawn((
            ImageNode::new(assets.load(def.painting)),
            Node {
                position_type: PositionType::Absolute,
                width: percent(100),
                aspect_ratio: Some(1.0 / def.painting_aspect),
                overflow: Overflow::clip(),
                ..default()
            },
            Painting,
        ))
        .id();
    for (i, glow) in def.glows.iter().enumerate() {
        let height = glow.width * glow.aspect / def.painting_aspect;
        commands.spawn((
            ImageNode { color: clear, ..ImageNode::new(assets.load(glow.image)) },
            Node {
                position_type: PositionType::Absolute,
                width: percent(glow.width * 100.0),
                height: percent(height * 100.0),
                left: percent((glow.center.x - glow.width / 2.0) * 100.0),
                top: percent((glow.center.y - height / 2.0) * 100.0),
                ..default()
            },
            UiTransform::default(),
            GlowLight(i),
            ChildOf(painting),
        ));
    }
    for (i, wisps) in def.wisps.iter().enumerate() {
        for k in 0..wisps.count {
            commands.spawn((
                ImageNode { color: clear, ..ImageNode::new(assets.load(wisps.image)) },
                Node { position_type: PositionType::Absolute, aspect_ratio: Some(1.0), ..default() },
                Puff { wisps: i, phase: k as f32 / wisps.count as f32 },
                ChildOf(painting),
            ));
        }
    }
    let frame = commands.spawn((Node { position_type: PositionType::Absolute, overflow: Overflow::clip(), ..default() }, IntroFrame)).id();
    commands.entity(frame).add_child(painting).with_children(|frame| {
        frame.spawn((
            Text::default(),
            TextFont::default(),
            TextColor(clear),
            TextLayout::justify(Justify::Center),
            TextShadow { offset: Vec2::splat(2.0), color: clear },
            Node { position_type: PositionType::Absolute, width: percent(100), bottom: percent(9), ..default() },
            Caption,
        ));
        frame.spawn((
            ImageNode { color: clear, ..ImageNode::new(assets.load(def.title)) },
            Node {
                position_type: PositionType::Absolute,
                width: percent(66),
                left: percent(17),
                top: percent(10),
                aspect_ratio: Some(TITLE_ASPECT),
                ..default()
            },
            UiTransform::default(),
            Title,
        ));
        frame.spawn((
            Text::new("Click to begin"),
            TextFont::default(),
            TextColor(clear),
            TextLayout::justify(Justify::Center),
            TextShadow { offset: Vec2::splat(2.0), color: clear },
            Node { position_type: PositionType::Absolute, width: percent(100), bottom: percent(11), ..default() },
            Prompt,
        ));
        frame.spawn((
            Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
            BackgroundColor(clear),
            Flash,
        ));
        frame.spawn((
            Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
            BackgroundColor(Color::BLACK),
            Fade,
        ));
    });
    commands
        .spawn((
            Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
            BackgroundColor(Color::BLACK),
            GlobalZIndex(100),
            IntroRoot,
        ))
        .add_child(frame);
    let volume = if sound.0 { INTRO_VOLUME } else { 0.0 };
    commands.spawn((
        AudioPlayer::new(assets.load(def.music)),
        PlaybackSettings::DESPAWN.with_volume(Volume::Linear(volume)),
        IntroMusic,
    ));
}

fn despawn_intro(mut commands: Commands, entities: Query<Entity, Or<(With<IntroRoot>, With<IntroMusic>, With<TitleMusic>)>>) {
    for entity in &entities {
        commands.entity(entity).despawn();
    }
}

/// Keep the timeline in step with the music, which may take a moment to load.
fn advance(
    mut commands: Commands,
    time: Res<Time>,
    assets: Res<AssetServer>,
    levels: Res<Levels>,
    level: Res<CurrentLevel>,
    mut intro: ResMut<Intro>,
    music: Query<&AudioSink, With<IntroMusic>>,
) {
    let def = &levels.0[level.0].intro;
    let dt = time.delta_secs();
    if let Some(sink) = music.iter().next() {
        // Advance smoothly every frame. The music reports its position in coarse steps,
        // so only use it to pull the timeline back if it has really drifted.
        intro.time += dt;
        let position = sink.position().as_secs_f32();
        if position > 0.0 && position != intro.last_position {
            intro.last_position = position;
            let heard = intro.music_offset + position;
            if (heard - intro.time).abs() > 0.35 {
                intro.time = heard;
            }
        }
    } else if intro.time == 0.0 && intro.waited < 4.0 {
        intro.waited += dt; // still loading: hold at the start, but don't wait forever
    } else {
        intro.time += dt;
    }
    if intro.time > def.music_length - 1.0 && intro.title_loop.is_none() {
        intro.title_loop = Some(intro.time);
        commands.spawn((
            AudioPlayer::new(assets.load(def.title_loop)),
            PlaybackSettings::LOOP.with_volume(Volume::Linear(0.0)),
            TitleMusic,
        ));
    }
}

/// A click, tap or key skips to the title; at the title it starts the game.
#[allow(clippy::too_many_arguments)]
fn input(
    mut commands: Commands,
    mouse: Res<ButtonInput<MouseButton>>,
    keys: Res<ButtonInput<KeyCode>>,
    touches: Res<Touches>,
    assets: Res<AssetServer>,
    levels: Res<Levels>,
    level: Res<CurrentLevel>,
    mut intro: ResMut<Intro>,
    music: Query<Entity, With<IntroMusic>>,
) {
    let def = &levels.0[level.0].intro;
    let pressed = mouse.just_pressed(MouseButton::Left)
        || touches.iter_just_pressed().next().is_some()
        || keys.any_just_pressed([KeyCode::Space, KeyCode::Enter, KeyCode::Escape]);
    if !pressed || intro.leaving.is_some() {
        return;
    }
    if intro.time < def.hit - SKIP_LEAD {
        // Jump to just before the title lands. Bevy can't seek inside an OGG file, so
        // switch to a copy of the music that starts there.
        for entity in &music {
            commands.entity(entity).despawn();
        }
        intro.time = def.hit - SKIP_LEAD;
        intro.music_offset = def.hit - SKIP_LEAD;
        intro.last_position = 0.0;
        intro.waited = f32::MAX;
        commands.spawn((
            AudioPlayer::new(assets.load(def.music_tail)),
            PlaybackSettings::DESPAWN.with_volume(Volume::Linear(0.0)), // `animate` sets the volume
            IntroMusic,
        ));
    } else if intro.time > def.hit + 1.0 {
        intro.leaving = Some(0.0);
    }
}

pub fn smoothstep(x: f32) -> f32 {
    let x = x.clamp(0.0, 1.0);
    x * x * (3.0 - 2.0 * x)
}

/// Fade in and out over `ramp` seconds within [start, end].
fn window(t: f32, start: f32, end: f32, ramp: f32) -> f32 {
    smoothstep((t - start) / ramp).min(smoothstep((end - t) / ramp))
}

/// The camera's height at time `t`, easing from one keyframe to the next.
fn pan_at(pan: &[(f32, f32)], t: f32) -> f32 {
    let Some(&(_, first)) = pan.first() else {
        return 0.0;
    };
    let mut value = first;
    for pair in pan.windows(2) {
        let ((t0, v0), (t1, v1)) = (pair[0], pair[1]);
        if t >= t0 {
            value = v0 + (v1 - v0) * smoothstep((t - t0) / (t1 - t0).max(0.001));
        }
    }
    value
}

/// A glow's brightness and how open it is (its height, for eyes), at time `t`.
fn glow_at(life: &Life, t: f32) -> (f32, f32) {
    let flicker = 0.78 + 0.12 * (t * 7.3).sin() + 0.1 * (t * 13.1 + 1.7).sin();
    match *life {
        Life::Dies(out) => {
            let alpha = if t < out - 1.2 {
                flicker * smoothstep(t / 2.0)
            } else if t < out - 0.7 {
                1.0
            } else {
                flicker * smoothstep((out + 0.8 - t) / 1.5)
            };
            (alpha, 1.0)
        }
        Life::Opens(at) => {
            let since = t - at;
            if since < 0.0 {
                return (0.0, 0.0);
            }
            // Open slowly the first time; afterwards a quick blink every few seconds.
            let open = smoothstep(since / 0.6);
            let blink = (since - 3.0).rem_euclid(4.7);
            let lid = if since > 3.0 && blink < 0.22 { (blink / 0.11 - 1.0).abs() } else { 1.0 };
            let pulse = 0.88 + 0.12 * (t * 2.3).sin();
            (smoothstep(since / 0.3) * pulse, open * lid)
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn animate(
    time: Res<Time>,
    window_q: Single<&Window>,
    ui_scale: Res<UiScale>,
    sound: Res<SoundOn>,
    levels: Res<Levels>,
    mut intro: ResMut<Intro>,
    mut next: ResMut<NextState<Screen>>,
    mut frame: Single<&mut Node, (With<IntroFrame>, Without<Painting>, Without<Puff>)>,
    mut painting: Single<&mut Node, (With<Painting>, Without<IntroFrame>, Without<Puff>)>,
    mut glows: Query<(&GlowLight, &mut ImageNode, &mut UiTransform), Without<Title>>,
    mut puffs: Query<(&Puff, &mut ImageNode, &mut Node), (Without<GlowLight>, Without<Title>, Without<IntroFrame>, Without<Painting>)>,
    title: Single<(&mut ImageNode, &mut UiTransform), (With<Title>, Without<GlowLight>, Without<Puff>)>,
    caption: Single<(&mut Text, &mut TextColor, &mut TextFont, &mut TextShadow), (With<Caption>, Without<Prompt>)>,
    prompt: Single<(&mut TextColor, &mut TextFont, &mut TextShadow), (With<Prompt>, Without<Caption>)>,
    mut veils: Query<(&mut BackgroundColor, Has<Flash>), Or<(With<Fade>, With<Flash>)>>,
    mut music: Query<(&mut AudioSink, Has<TitleMusic>), Or<(With<IntroMusic>, With<TitleMusic>)>>,
) {
    let def = &levels.0[intro.level].intro;
    let t = intro.time;
    let k = ui_scale.0;

    // The 16:9 frame, as large as fits.
    let (ww, wh) = (window_q.width(), window_q.height());
    let (fw, fh) = if ww / wh > FRAME_ASPECT { (wh * FRAME_ASPECT, wh) } else { (ww, ww / FRAME_ASPECT) };
    frame.left = px((ww - fw) / 2.0 / k);
    frame.top = px((wh - fh) / 2.0 / k);
    frame.width = px(fw / k);
    frame.height = px(fh / k);

    // Pan across the tall painting.
    let travel = (fw * def.painting_aspect - fh).max(0.0);
    painting.top = px(-travel * (1.0 - pan_at(def.pan, t)) / k);

    for (GlowLight(i), mut image, mut transform) in &mut glows {
        let (alpha, open) = glow_at(&def.glows[*i].life, t);
        image.color = Color::srgba(1.0, 1.0, 1.0, alpha);
        transform.scale = Vec2::new(1.0, open.max(0.02));
    }

    // Each puff rises from the origin, swelling, leaning with the breeze and fading.
    let painting_w = fw / k;
    for (puff, mut image, mut node) in &mut puffs {
        let w = &def.wisps[puff.wisps];
        let age = (t / w.life + puff.phase).fract();
        let size = w.width * (1.0 + 2.6 * age);
        let x = w.origin.x + w.lean * age * age - size / 2.0;
        let y_px = w.origin.y * painting_w * def.painting_aspect - (w.rise * age + size / 2.0) * painting_w;
        node.left = percent(x * 100.0);
        node.top = px(y_px);
        node.width = px(size * painting_w);
        let alpha = w.color[3] * smoothstep(age / 0.12) * (1.0 - age).powf(0.9) * smoothstep(t / 1.5);
        image.color = Color::srgba(w.color[0], w.color[1], w.color[2], alpha);
    }

    // Captions, Monkey Island style.
    let (mut text, mut color, mut font, mut shadow) = caption.into_inner();
    let current = def.captions.iter().find(|(start, end, _)| t >= *start - 0.1 && t <= *end + 0.1);
    let alpha = current.map_or(0.0, |(start, end, _)| window(t, *start, *end, 0.9));
    if let Some((_, _, line)) = current
        && text.0 != *line
    {
        text.0 = line.to_string();
    }
    color.0 = Color::srgba(0.93, 0.89, 0.8, alpha);
    shadow.color = Color::srgba(0.0, 0.0, 0.0, 0.9 * alpha); // or the shadow lingers as a ghost
    let caption_size = FontSize::Px((fh * 0.042).max(14.0) / k);
    if font.font_size != caption_size {
        font.font_size = caption_size;
    }

    // The title lands on the hit: a flash of light, then it settles into place.
    let (mut logo, mut transform) = title.into_inner();
    let shown = smoothstep((t - def.hit) / 1.4);
    logo.color = Color::srgba(1.0, 1.0, 1.0, shown);
    transform.scale = Vec2::splat(1.0 + 0.12 * (1.0 - smoothstep((t - def.hit) / 3.0)));
    let flash_alpha = if t >= def.hit { 0.55 * (1.0 - (t - def.hit) / 0.35).max(0.0).powi(2) } else { 0.0 };
    let [fr, fg, fb] = def.flash;

    let (mut prompt_color, mut prompt_font, mut prompt_shadow) = prompt.into_inner();
    let pulse = 0.6 + 0.4 * (time.elapsed_secs() * 2.4).sin();
    let prompt_alpha = smoothstep((t - def.prompt) / 1.5) * pulse;
    prompt_color.0 = Color::srgba(0.94, 0.82, 0.55, prompt_alpha);
    prompt_shadow.color = Color::srgba(0.0, 0.0, 0.0, 0.9 * prompt_alpha);
    let prompt_size = FontSize::Px((fh * 0.036).max(13.0) / k);
    if prompt_font.font_size != prompt_size {
        prompt_font.font_size = prompt_size;
    }

    // Fade in from black at the start; fade out to black when leaving.
    let leaving = intro.leaving.map(|s| s / LEAVE_SECONDS).unwrap_or(0.0);
    let fade_in = 1.0 - smoothstep(t / 2.8);
    for (mut color, is_flash) in &mut veils {
        color.0 = if is_flash { Color::srgba(fr, fg, fb, flash_alpha) } else { Color::srgba(0.0, 0.0, 0.0, fade_in.max(leaving)) };
    }

    // Music: the title loop fades in as the intro piece ends; everything fades on leaving.
    let volume = if sound.0 { INTRO_VOLUME } else { 0.0 } * (1.0 - leaving);
    let loop_in = intro.title_loop.map_or(0.0, |start| smoothstep((t - start) / 3.0));
    for (mut sink, is_title_loop) in &mut music {
        sink.set_volume(Volume::Linear(if is_title_loop { volume * loop_in } else { volume }));
    }

    if let Some(seconds) = intro.leaving.as_mut() {
        *seconds += time.delta_secs();
        if *seconds >= LEAVE_SECONDS {
            next.set(Screen::Playing);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pan_eases_between_keyframes() {
        let pan = [(0.0, 0.0), (10.0, 1.0), (20.0, 0.5)];
        assert_eq!(pan_at(&pan, -1.0), 0.0);
        assert_eq!(pan_at(&pan, 5.0), 0.5);
        assert_eq!(pan_at(&pan, 10.0), 1.0);
        assert_eq!(pan_at(&pan, 30.0), 0.5);
    }
}

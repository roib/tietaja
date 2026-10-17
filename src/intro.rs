//! The opening: night over the village, the last ember dying, the view tilting up to the
//! northern lights, and the title landing on the music's big hit. Click to skip ahead to
//! the title, and click again to start the game.

use bevy::{
    audio::{AudioSinkPlayback, Volume},
    prelude::*,
};

use crate::SoundOn;

#[derive(States, Default, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Screen {
    #[default]
    Intro,
    Playing,
}

// The timeline in seconds, matched to music/intro.ogg (INTRO_* in tools/make_audio.py).
const FIRE_OUT: f32 = 16.0;
const TILT: (f32, f32) = (19.0, 27.2);
const HIT: f32 = 28.0;
const PROMPT: f32 = 33.0;
/// Skipping lands this long before the hit, where music/intro_tail.ogg begins.
const SKIP_LEAD: f32 = 0.6;
const MUSIC_LENGTH: f32 = 54.0;
const CAPTIONS: [(f32, f32, &str); 3] = [
    (2.6, 8.4, "Häme, long ago, in the time of the old words…"),
    (9.2, 14.6, "Every hearth kept a fire that had never once gone out."),
    (15.6, 20.6, "Until one night, one did."),
];

/// The night painting's height over its width, and where its ember glows (as fractions).
const NIGHT_ASPECT: f32 = 1440.0 / 1280.0;
const EMBER: Vec2 = Vec2::new(160.0 / 320.0, 342.0 / 360.0);
const EMBER_WIDTH: f32 = 0.09;
const TITLE_ASPECT: f32 = 1600.0 / 520.0;
/// The intro is shown in a 16:9 frame, as large as fits the window.
const FRAME_ASPECT: f32 = 16.0 / 9.0;
const INTRO_VOLUME: f32 = 0.85;
const LEAVE_SECONDS: f32 = 1.2;

#[derive(Resource, Default)]
struct Intro {
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
struct Night;

#[derive(Component)]
struct Ember;

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
            .init_resource::<Intro>()
            .add_systems(OnEnter(Screen::Intro), spawn_intro)
            .add_systems(Update, (advance, input, animate).chain().run_if(in_state(Screen::Intro)))
            .add_systems(OnExit(Screen::Intro), despawn_intro);
    }
}

fn spawn_intro(mut commands: Commands, assets: Res<AssetServer>, sound: Res<SoundOn>) {
    let clear = Color::NONE;
    commands.spawn((
        Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
        BackgroundColor(Color::BLACK),
        GlobalZIndex(100),
        IntroRoot,
        children![(
            Node { position_type: PositionType::Absolute, overflow: Overflow::clip(), ..default() },
            IntroFrame,
            children![
                (
                    ImageNode::new(assets.load("intro/night.png")),
                    Node {
                        position_type: PositionType::Absolute,
                        width: percent(100),
                        aspect_ratio: Some(1.0 / NIGHT_ASPECT),
                        ..default()
                    },
                    Night,
                    children![(
                        ImageNode { color: clear, ..ImageNode::new(assets.load("intro/ember.png")) },
                        Node {
                            position_type: PositionType::Absolute,
                            width: percent(EMBER_WIDTH * 100.0),
                            aspect_ratio: Some(1.0),
                            left: percent((EMBER.x - EMBER_WIDTH / 2.0) * 100.0),
                            top: percent((EMBER.y - EMBER_WIDTH / 2.0 / NIGHT_ASPECT) * 100.0),
                            ..default()
                        },
                        Ember,
                    )],
                ),
                (
                    Text::default(),
                    TextFont::default(),
                    TextColor(clear),
                    TextLayout::justify(Justify::Center),
                    TextShadow { offset: Vec2::splat(2.0), color: clear },
                    Node { position_type: PositionType::Absolute, width: percent(100), bottom: percent(9), ..default() },
                    Caption,
                ),
                (
                    ImageNode { color: clear, ..ImageNode::new(assets.load("intro/title.png")) },
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
                ),
                (
                    Text::new("Click to begin"),
                    TextFont::default(),
                    TextColor(clear),
                    TextLayout::justify(Justify::Center),
                    TextShadow { offset: Vec2::splat(2.0), color: clear },
                    Node { position_type: PositionType::Absolute, width: percent(100), bottom: percent(11), ..default() },
                    Prompt,
                ),
                (
                    Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
                    BackgroundColor(Color::srgba(1.0, 0.86, 0.55, 0.0)),
                    Flash,
                ),
                (
                    Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
                    BackgroundColor(Color::BLACK),
                    Fade,
                ),
            ],
        )],
    ));
    let volume = if sound.0 { INTRO_VOLUME } else { 0.0 };
    commands.spawn((
        AudioPlayer::new(assets.load("music/intro.ogg")),
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
    mut intro: ResMut<Intro>,
    music: Query<&AudioSink, With<IntroMusic>>,
) {
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
    if intro.time > MUSIC_LENGTH - 1.0 && intro.title_loop.is_none() {
        start_title_loop(&mut commands, &assets, &mut intro);
    }
}

fn start_title_loop(commands: &mut Commands, assets: &AssetServer, intro: &mut Intro) {
    intro.title_loop = Some(intro.time);
    commands.spawn((
        AudioPlayer::new(assets.load("music/title.ogg")),
        PlaybackSettings::LOOP.with_volume(Volume::Linear(0.0)),
        TitleMusic,
    ));
}

/// A click, tap or key skips to the title; at the title it starts the game.
fn input(
    mut commands: Commands,
    mouse: Res<ButtonInput<MouseButton>>,
    keys: Res<ButtonInput<KeyCode>>,
    touches: Res<Touches>,
    assets: Res<AssetServer>,
    mut intro: ResMut<Intro>,
    music: Query<Entity, With<IntroMusic>>,
) {
    let pressed = mouse.just_pressed(MouseButton::Left)
        || touches.iter_just_pressed().next().is_some()
        || keys.any_just_pressed([KeyCode::Space, KeyCode::Enter, KeyCode::Escape]);
    if !pressed || intro.leaving.is_some() {
        return;
    }
    if intro.time < HIT - SKIP_LEAD {
        // Jump to just before the title lands. Bevy can't seek inside an OGG file, so
        // switch to a copy of the music that starts there.
        for entity in &music {
            commands.entity(entity).despawn();
        }
        intro.time = HIT - SKIP_LEAD;
        intro.music_offset = HIT - SKIP_LEAD;
        intro.last_position = 0.0;
        intro.waited = f32::MAX;
        commands.spawn((
            AudioPlayer::new(assets.load("music/intro_tail.ogg")),
            PlaybackSettings::DESPAWN.with_volume(Volume::Linear(0.0)), // `animate` sets the volume
            IntroMusic,
        ));
    } else if intro.time > HIT + 1.0 {
        intro.leaving = Some(0.0);
    }
}

fn smoothstep(x: f32) -> f32 {
    let x = x.clamp(0.0, 1.0);
    x * x * (3.0 - 2.0 * x)
}

/// Fade in and out over `ramp` seconds within [start, end].
fn window(t: f32, start: f32, end: f32, ramp: f32) -> f32 {
    smoothstep((t - start) / ramp).min(smoothstep((end - t) / ramp))
}

#[allow(clippy::too_many_arguments)]
fn animate(
    time: Res<Time>,
    window_q: Single<&Window>,
    ui_scale: Res<UiScale>,
    sound: Res<SoundOn>,
    mut intro: ResMut<Intro>,
    mut next: ResMut<NextState<Screen>>,
    mut frame: Single<&mut Node, (With<IntroFrame>, Without<Night>)>,
    mut night: Single<&mut Node, (With<Night>, Without<IntroFrame>)>,
    mut ember: Single<&mut ImageNode, (With<Ember>, Without<Title>)>,
    title: Single<(&mut ImageNode, &mut UiTransform), (With<Title>, Without<Ember>)>,
    caption: Single<(&mut Text, &mut TextColor, &mut TextFont, &mut TextShadow), (With<Caption>, Without<Prompt>)>,
    prompt: Single<(&mut TextColor, &mut TextFont, &mut TextShadow), (With<Prompt>, Without<Caption>)>,
    mut fade: Single<&mut BackgroundColor, (With<Fade>, Without<Flash>)>,
    mut flash: Single<&mut BackgroundColor, (With<Flash>, Without<Fade>)>,
    mut music: Query<(&mut AudioSink, Has<TitleMusic>), Or<(With<IntroMusic>, With<TitleMusic>)>>,
) {
    let t = intro.time;
    let k = ui_scale.0;

    // The 16:9 frame, as large as fits.
    let (ww, wh) = (window_q.width(), window_q.height());
    let (fw, fh) = if ww / wh > FRAME_ASPECT { (wh * FRAME_ASPECT, wh) } else { (ww, ww / FRAME_ASPECT) };
    frame.left = px((ww - fw) / 2.0 / k);
    frame.top = px((wh - fh) / 2.0 / k);
    frame.width = px(fw / k);
    frame.height = px(fh / k);

    // Start low on the village; drift up a little, then tilt up to the sky.
    let travel = (fw * NIGHT_ASPECT - fh).max(0.0);
    let rise = 0.06 * smoothstep(t / TILT.0) + 0.94 * smoothstep((t - TILT.0) / (TILT.1 - TILT.0));
    night.top = px(-travel * (1.0 - rise) / k);

    // The last ember flickers, flares once, and dies.
    let flicker = 0.78 + 0.12 * (t * 7.3).sin() + 0.1 * (t * 13.1 + 1.7).sin();
    let ember_alpha = if t < FIRE_OUT - 1.2 {
        flicker * smoothstep(t / 2.0)
    } else if t < FIRE_OUT - 0.7 {
        1.0
    } else {
        flicker * smoothstep((FIRE_OUT + 0.8 - t) / 1.5)
    };
    ember.color = Color::srgba(1.0, 1.0, 1.0, ember_alpha);

    // Captions, Monkey Island style.
    let (mut text, mut color, mut font, mut shadow) = caption.into_inner();
    let current = CAPTIONS.iter().find(|(start, end, _)| t >= *start - 0.1 && t <= *end + 0.1);
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

    // The title lands on the hit: a flash of firelight, then it settles into place.
    let (mut logo, mut transform) = title.into_inner();
    let shown = smoothstep((t - HIT) / 1.4);
    logo.color = Color::srgba(1.0, 1.0, 1.0, shown);
    transform.scale = Vec2::splat(1.0 + 0.12 * (1.0 - smoothstep((t - HIT) / 3.0)));
    let flash_alpha = if t >= HIT { 0.55 * (1.0 - (t - HIT) / 0.35).max(0.0).powi(2) } else { 0.0 };
    flash.0 = Color::srgba(1.0, 0.94, 0.78, flash_alpha);

    let (mut prompt_color, mut prompt_font, mut prompt_shadow) = prompt.into_inner();
    let pulse = 0.6 + 0.4 * (time.elapsed_secs() * 2.4).sin();
    let prompt_alpha = smoothstep((t - PROMPT) / 1.5) * pulse;
    prompt_color.0 = Color::srgba(0.94, 0.82, 0.55, prompt_alpha);
    prompt_shadow.color = Color::srgba(0.0, 0.0, 0.0, 0.9 * prompt_alpha);
    let prompt_size = FontSize::Px((fh * 0.036).max(13.0) / k);
    if prompt_font.font_size != prompt_size {
        prompt_font.font_size = prompt_size;
    }

    // Fade in from black at the start; fade out to black when leaving.
    let leaving = intro.leaving.map(|s| s / LEAVE_SECONDS).unwrap_or(0.0);
    let fade_in = 1.0 - smoothstep(t / 2.8);
    fade.0 = Color::srgba(0.0, 0.0, 0.0, fade_in.max(leaving));

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

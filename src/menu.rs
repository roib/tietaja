//! The first screen: the title over the northern lights, and a painted card for each tale.
//! Choosing one fades to black and plays that tale's opening.

use bevy::{
    audio::{AudioSinkPlayback, Volume},
    picking::hover::Hovered,
    prelude::*,
    ui_widgets::{Activate, Button, observe},
};

use crate::SoundOn;
use crate::intro::{FRAME_ASPECT, Screen, smoothstep};
use crate::levels::{CurrentLevel, Levels};

const LOGO_ASPECT: f32 = 1600.0 / 400.0;
const CARD_ASPECT: f32 = 4.0 / 3.0;
const BACKDROP_ASPECT: f32 = 1440.0 / 1280.0;
const MUSIC: &str = "music/title.ogg";
const MUSIC_VOLUME: f32 = 0.6;
const FADE_IN: f32 = 2.2;
const LEAVE_SECONDS: f32 = 1.4;
const GILT: Color = Color::srgb(0.74, 0.6, 0.32);
const GILT_BRIGHT: Color = Color::srgb(1.0, 0.86, 0.55);
const LABEL: Color = Color::srgb(0.85, 0.78, 0.64);

#[derive(Resource, Default)]
struct Menu {
    time: f32,
    /// The card the keyboard (or the pointer) is on.
    selected: usize,
    /// Seconds since a tale was chosen.
    leaving: Option<f32>,
}

#[derive(Component)]
struct MenuRoot;

#[derive(Component)]
struct MenuFrame;

#[derive(Component)]
struct Backdrop;

#[derive(Component)]
struct Heading;

#[derive(Component)]
struct Card(usize);

#[derive(Component)]
struct CardLabel(usize);

#[derive(Component)]
struct MenuFade;

#[derive(Component)]
struct MenuMusic;

pub struct MenuPlugin;

impl Plugin for MenuPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(OnEnter(Screen::Menu), spawn_menu)
            .add_systems(Update, (input, animate).chain().run_if(in_state(Screen::Menu)))
            .add_systems(OnExit(Screen::Menu), despawn_menu);
    }
}

fn spawn_menu(mut commands: Commands, assets: Res<AssetServer>, levels: Res<Levels>, current: Res<CurrentLevel>) {
    commands.insert_resource(Menu { selected: current.0, ..default() });
    let frame = commands.spawn((Node { position_type: PositionType::Absolute, overflow: Overflow::clip(), ..default() }, MenuFrame)).id();
    commands.entity(frame).with_children(|frame| {
        frame.spawn((
            ImageNode::new(assets.load("intro/night.png")),
            Node { position_type: PositionType::Absolute, width: percent(100), aspect_ratio: Some(1.0 / BACKDROP_ASPECT), ..default() },
            Backdrop,
        ));
        // Darken the sky toward the bottom, so the cards stand out.
        frame.spawn((
            Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
            BackgroundGradient::from(LinearGradient::to_bottom(vec![
                ColorStop::auto(Color::srgba(0.0, 0.0, 0.02, 0.15)),
                ColorStop::auto(Color::srgba(0.0, 0.0, 0.02, 0.55)),
                ColorStop::auto(Color::srgba(0.01, 0.01, 0.03, 0.9)),
            ])),
        ));
        frame.spawn((
            ImageNode::new(assets.load("intro/logo.png")),
            Node {
                position_type: PositionType::Absolute,
                width: percent(54),
                left: percent(23),
                top: percent(5),
                aspect_ratio: Some(LOGO_ASPECT),
                ..default()
            },
        ));
        frame.spawn((
            Text::new("Choose a tale"),
            TextFont::default(),
            TextColor(LABEL),
            TextLayout::justify(Justify::Center),
            TextShadow { offset: Vec2::splat(2.0), color: Color::srgba(0.0, 0.0, 0.0, 0.9) },
            Node { position_type: PositionType::Absolute, width: percent(100), top: percent(27), ..default() },
            Heading,
        ));
        let count = levels.0.len() as f32;
        let (card_w, gap) = (34.0, 8.0);
        let row_left = (100.0 - count * card_w - (count - 1.0) * gap) / 2.0;
        for (i, level) in levels.0.iter().enumerate() {
            let title = level.story.title.clone().unwrap_or_default();
            frame
                .spawn((
                    Button,
                    Hovered::default(),
                    Node {
                        position_type: PositionType::Absolute,
                        width: percent(card_w),
                        left: percent(row_left + i as f32 * (card_w + gap)),
                        top: percent(34),
                        flex_direction: FlexDirection::Column,
                        ..default()
                    },
                    UiTransform::default(),
                    Card(i),
                    observe(move |_: On<Activate>, mut menu: ResMut<Menu>| {
                        if menu.leaving.is_none() && menu.time > 0.6 {
                            menu.selected = i;
                            menu.leaving = Some(0.0);
                        }
                    }),
                ))
                .with_children(|card| {
                    card.spawn((
                        Node { width: percent(100), aspect_ratio: Some(CARD_ASPECT), border: UiRect::all(px(3)), ..default() },
                        BorderColor::all(GILT),
                        BoxShadow::new(Color::srgba(0.0, 0.0, 0.0, 0.8), px(0), px(6), px(2), px(18)),
                        children![(
                            ImageNode::new(assets.load(level.card)),
                            Node { width: percent(100), height: percent(100), ..default() },
                        )],
                    ));
                    card.spawn((
                        Text::new(format!("{} · {title}", level.numeral)),
                        TextFont::default(),
                        TextColor(LABEL),
                        TextLayout::justify(Justify::Center),
                        TextShadow { offset: Vec2::splat(2.0), color: Color::srgba(0.0, 0.0, 0.0, 0.9) },
                        Node { width: percent(100), margin: UiRect::top(percent(4)), ..default() },
                        CardLabel(i),
                    ));
                });
        }
        frame.spawn((
            Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
            BackgroundColor(Color::BLACK),
            Pickable::IGNORE,
            MenuFade,
        ));
    });
    commands
        .spawn((
            Node { position_type: PositionType::Absolute, width: percent(100), height: percent(100), ..default() },
            BackgroundColor(Color::BLACK),
            GlobalZIndex(100),
            MenuRoot,
        ))
        .add_child(frame);
    commands.spawn((AudioPlayer::new(assets.load(MUSIC)), PlaybackSettings::LOOP.with_volume(Volume::Linear(0.0)), MenuMusic));
}

fn despawn_menu(mut commands: Commands, entities: Query<Entity, Or<(With<MenuRoot>, With<MenuMusic>)>>) {
    for entity in &entities {
        commands.entity(entity).despawn();
    }
}

/// Arrow keys move between the cards and Enter chooses; the pointer selects what it moves onto.
fn input(
    keys: Res<ButtonInput<KeyCode>>,
    levels: Res<Levels>,
    cards: Query<(&Card, &Hovered), Changed<Hovered>>,
    mut menu: ResMut<Menu>,
) {
    if menu.leaving.is_some() {
        return;
    }
    let count = levels.0.len();
    if keys.any_just_pressed([KeyCode::ArrowRight, KeyCode::KeyD, KeyCode::Tab]) {
        menu.selected = (menu.selected + 1) % count;
    }
    if keys.any_just_pressed([KeyCode::ArrowLeft, KeyCode::KeyA]) {
        menu.selected = (menu.selected + count - 1) % count;
    }
    // Only when the pointer moves onto a card, so a resting mouse doesn't fight the keys.
    for (Card(i), hovered) in &cards {
        if hovered.get() {
            menu.selected = *i;
        }
    }
    if keys.any_just_pressed([KeyCode::Enter, KeyCode::Space]) && menu.time > 0.6 {
        menu.leaving = Some(0.0);
    }
}

#[allow(clippy::too_many_arguments)]
fn animate(
    time: Res<Time>,
    window: Single<&Window>,
    ui_scale: Res<UiScale>,
    sound: Res<SoundOn>,
    mut menu: ResMut<Menu>,
    mut current: ResMut<CurrentLevel>,
    mut next: ResMut<NextState<Screen>>,
    mut frame: Single<&mut Node, (With<MenuFrame>, Without<Backdrop>)>,
    mut backdrop: Single<&mut Node, (With<Backdrop>, Without<MenuFrame>)>,
    mut heading: Single<&mut TextFont, (With<Heading>, Without<CardLabel>)>,
    mut cards: Query<(&Card, &mut UiTransform, &Children)>,
    mut borders: Query<&mut BorderColor>,
    mut labels: Query<(&CardLabel, &mut TextColor, &mut TextFont), Without<Heading>>,
    mut fade: Single<&mut BackgroundColor, With<MenuFade>>,
    mut music: Query<&mut AudioSink, With<MenuMusic>>,
) {
    let dt = time.delta_secs();
    menu.time += dt;
    let t = menu.time;
    let k = ui_scale.0;

    let (ww, wh) = (window.width(), window.height());
    let (fw, fh) = if ww / wh > FRAME_ASPECT { (wh * FRAME_ASPECT, wh) } else { (ww, ww / FRAME_ASPECT) };
    frame.left = px((ww - fw) / 2.0 / k);
    frame.top = px((wh - fh) / 2.0 / k);
    frame.width = px(fw / k);
    frame.height = px(fh / k);

    // The northern lights, drifting slowly up and down behind the title.
    backdrop.top = px(-fw * (0.2 + 0.03 * (t * 0.05).sin()) / k);

    let heading_size = FontSize::Px((fh * 0.034).max(13.0) / k);
    if heading.font_size != heading_size {
        heading.font_size = heading_size;
    }

    // The selected card lifts and its frame brightens; the other dims a little.
    let leaving = menu.leaving.map(|s| s / LEAVE_SECONDS).unwrap_or(0.0);
    for (Card(i), mut transform, children) in &mut cards {
        let selected = *i == menu.selected;
        let target = if selected { 1.05 + 0.03 * smoothstep(leaving * 3.0) } else { 1.0 };
        let scale = transform.scale.x + (target - transform.scale.x) * (dt * 10.0).min(1.0);
        transform.scale = Vec2::splat(scale);
        if let Ok(mut border) = borders.get_mut(children[0]) {
            let glow = if selected { 0.6 + 0.4 * (t * 2.6).sin().abs() } else { 0.0 };
            border.set_all(GILT.mix(&GILT_BRIGHT, glow));
        }
    }
    let label_size = FontSize::Px((fh * 0.036).max(13.0) / k);
    for (CardLabel(i), mut color, mut font) in &mut labels {
        color.0 = if *i == menu.selected { GILT_BRIGHT } else { LABEL };
        if font.font_size != label_size {
            font.font_size = label_size;
        }
    }

    fade.0 = Color::srgba(0.0, 0.0, 0.0, (1.0 - smoothstep(t / FADE_IN)).max(smoothstep(leaving)));
    let volume = if sound.0 { MUSIC_VOLUME } else { 0.0 } * smoothstep(t / 3.0) * (1.0 - leaving).max(0.0);
    for mut sink in &mut music {
        sink.set_volume(Volume::Linear(volume));
    }

    if let Some(seconds) = menu.leaving.as_mut() {
        *seconds += dt;
        if *seconds >= LEAVE_SECONDS {
            current.0 = menu.selected;
            next.set(Screen::Intro);
        }
    }
}

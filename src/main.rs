mod intro;
mod scenery;
mod story;

use std::collections::{HashMap, VecDeque};

use bevy::{
    audio::{AudioSinkPlayback, Volume},
    camera::{ScalingMode, Viewport, visibility::RenderLayers},
    picking::hover::Hovered,
    prelude::*,
    sprite::Anchor,
    ui_widgets::{Activate, Button, observe},
};
use intro::{IntroPlugin, Screen};
use scenery::SceneryPlugin;
use story::{Choice, Dialogue, GameState, ROOM_HEIGHT, ROOM_WIDTH, Step, Story, VOICE_SYLLABLES, Verb};

/// The painting and the verb panel beneath it form one framed block, centered in the
/// window. The panel is this fraction of the painting's height.
const PANEL_RATIO: f32 = 0.4;
const WALK_SPEED: f32 = 70.0;
const PLAYER_SIZE: Vec2 = Vec2::new(14.0, 40.0);
const PLAYER_HEIGHT: f32 = PLAYER_SIZE.y;

const PANEL_BG: Color = Color::srgb(0.1, 0.07, 0.05);
/// Like a painting hung on a dark wall: a wooden frame with a gilt fillet.
const WALL: Color = Color::srgb(0.06, 0.045, 0.035);
const FRAME_WOOD: Color = Color::srgb(0.2, 0.13, 0.075);
const FRAME_GILT: Color = Color::srgb(0.74, 0.6, 0.32);
const SENTENCE_COLOR: Color = Color::srgb(0.62, 0.84, 0.62);
const VERB_COLOR: Color = Color::srgb(0.55, 0.45, 0.32);
const VERB_HOVER: Color = Color::srgb(0.98, 0.86, 0.55);
const CHOICE_COLOR: Color = Color::srgb(0.75, 0.68, 0.9);

const FONT: &str = "fonts/NotoSerif-Medium.ttf";
const MUSIC_VOLUME: f32 = 0.45;
const VOICE_VOLUME: f32 = 0.5;
/// How fast music fades in and out, in volume per second.
const MUSIC_FADE: f32 = 0.6;

#[derive(Resource)]
struct StoryRes(Story);

/// Flags, inventory and room. The room view and inventory redraw when this changes.
#[derive(Resource)]
struct Game(GameState);

/// The running conversation, if any, and what it is currently showing.
#[derive(Resource, Default)]
struct Talk {
    dialogue: Option<Dialogue>,
    line: Option<(String, String)>,
    choices: Vec<Choice>,
}

#[derive(Resource)]
struct Ui {
    verb: Verb,
    held: Option<String>,
    hover: Option<String>,
}

#[derive(Resource)]
struct Player {
    pos: Vec2,
    target: Option<Vec2>,
    pending: Option<Action>,
    facing_left: bool,
    /// Distance walked, which picks the walk-cycle frame.
    walked: f32,
}

/// Vilja standing (frame 0, turned three-quarters) and her walk cycle in profile.
#[derive(Resource)]
struct PlayerFrames(Vec<Handle<Image>>);

/// Room units walked per frame of the walk cycle.
const STRIDE: f32 = 4.5;

#[derive(Clone)]
enum Action {
    Interact { verb: Verb, item: Option<String>, target: String, face_x: f32 },
    Exit { room: String, x: f32 },
}

/// The bundled font; Bevy's built-in one has no ä, ö or å.
#[derive(Resource)]
struct GameFont(Handle<Font>);

#[derive(Resource)]
struct SoundOn(bool);

/// Each speaker's babble syllables and how often they play.
#[derive(Resource, Default)]
struct VoiceBank(HashMap<String, (Vec<Handle<AudioSource>>, f32)>);

/// Syllables still to play for the current line: (seconds after line start, playback speed).
#[derive(Resource, Default)]
struct Babble {
    line: Option<(String, String)>,
    started: f32,
    queue: VecDeque<(f32, f32)>,
    rng: u64,
}

#[derive(Component)]
struct MusicTrack {
    path: String,
    volume: f32,
    fading_out: bool,
}

#[derive(Component)]
struct SceneCamera;

#[derive(Component)]
struct PlayerSprite;

#[derive(Component)]
struct SentenceText;

#[derive(Component)]
struct SpeechBox;

#[derive(Component)]
struct SpeechText;

#[derive(Component)]
struct Panel;

#[derive(Component)]
struct Frame;

#[derive(Component)]
struct VerbPanel;

#[derive(Component)]
struct VerbButton(Verb);

#[derive(Component)]
struct InventoryBar;

#[derive(Component)]
struct ItemButton(String);

#[derive(Component)]
struct ChoicePanel;

#[derive(Component)]
struct EndCard;

fn main() {
    let story = match Story::parse(include_str!("../assets/story.txt")) {
        Ok(story) => story,
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    };
    let (start_room, start_x) = story.start.clone();
    let floor = story.room(&start_room).floor;
    let talk = Talk { dialogue: story.intro.as_deref().map(Dialogue::new), ..default() };

    App::new()
        .add_plugins(
            DefaultPlugins
                .set(WindowPlugin {
                    primary_window: Some(Window {
                        title: "Tietäjä".into(),
                        fit_canvas_to_parent: true,
                        ..default()
                    }),
                    ..default()
                }),
        )
        .insert_resource(ClearColor(WALL))
        .insert_resource(Game(GameState { room: start_room, ..default() }))
        .insert_resource(Player {
            pos: Vec2::new(start_x, (floor.0 + floor.1) / 2.0),
            target: None,
            pending: None,
            facing_left: false,
            walked: 0.0,
        })
        .insert_resource(talk)
        .insert_resource(Ui { verb: Verb::Walk, held: None, hover: None })
        .insert_resource(StoryRes(story))
        .insert_resource(SoundOn(true))
        .insert_resource(Babble { rng: 0x9E37_79B9_7F4A_7C15, ..default() })
        .add_plugins((IntroPlugin, SceneryPlugin))
        .add_systems(Startup, setup)
        .add_systems(Update, (apply_font, toggle_sound, play_music.run_if(in_state(Screen::Playing)), play_babble, scale_ui))
        .add_systems(
            Update,
            (
                layout,
                // The game itself waits until the intro is over.
                (handle_pointer, hover_items, move_player, run_dialogue).run_if(in_state(Screen::Playing)),
            )
                .chain(),
        )
        .add_systems(
            Update,
            (
                sync_inventory.run_if(resource_changed::<Game>),
                sync_choices.run_if(resource_changed::<Talk>),
                draw_player,
                update_panel,
                update_speech,
                style_buttons,
            )
                .after(run_dialogue),
        )
        .run();
}

/// Room pixels (top-left origin, y down) to world units (centered, y up).
fn room_to_world(p: Vec2) -> Vec2 {
    Vec2::new(p.x - ROOM_WIDTH / 2.0, ROOM_HEIGHT / 2.0 - p.y)
}

fn world_to_room(p: Vec2) -> Vec2 {
    Vec2::new(p.x + ROOM_WIDTH / 2.0, ROOM_HEIGHT / 2.0 - p.y)
}

fn setup(mut commands: Commands, assets: Res<AssetServer>, story: Res<StoryRes>) {
    let frames: Vec<Handle<Image>> = std::iter::once(assets.load("chars/vilja_stand.png"))
        .chain((0..4).map(|i| assets.load(format!("chars/vilja_walk_{i}.png"))))
        .collect();
    commands.insert_resource(PlayerFrames(frames.clone()));
    commands.insert_resource(GameFont(assets.load(FONT)));
    let mut voices = VoiceBank::default();
    for (name, character) in &story.0.characters {
        if let Some(voice) = &character.voice {
            let clips = (0..VOICE_SYLLABLES).map(|i| assets.load(format!("{}/{i}.ogg", voice.dir))).collect();
            voices.0.insert(name.clone(), (clips, voice.rate));
        }
    }
    commands.insert_resource(voices);

    // Scene camera: shows the 320x144 room scaled up, in the top part of the window.
    commands.spawn((
        Camera2d,
        Projection::Orthographic(OrthographicProjection {
            scaling_mode: ScalingMode::AutoMin { min_width: ROOM_WIDTH, min_height: ROOM_HEIGHT },
            ..OrthographicProjection::default_2d()
        }),
        SceneCamera,
    ));
    // UI camera: covers the whole window, draws no sprites, only the interface.
    commands.spawn((
        Camera2d,
        Camera { order: 1, clear_color: ClearColorConfig::None, ..default() },
        RenderLayers::layer(1),
        IsDefaultUiCamera,
    ));

    commands.spawn((
        Sprite { custom_size: Some(PLAYER_SIZE), ..Sprite::from_image(frames[0].clone()) },
        Anchor::BOTTOM_CENTER,
        PlayerSprite,
        // A soft shadow at her feet, cast to the right like the painted shadows.
        children![(
            Sprite { custom_size: Some(Vec2::new(16.0, 4.0)), ..Sprite::from_image(assets.load("objects/shadow.png")) },
            Transform::from_xyz(3.0, 0.5, -0.0005),
        )],
    ));

    // Speech floats above whoever is talking.
    commands.spawn((
        Node { position_type: PositionType::Absolute, display: Display::None, ..default() },
        SpeechBox,
        children![(
            Text::default(),
            TextFont { font_size: FontSize::Px(22.0), ..default() },
            TextLayout::justify(Justify::Center),
            TextShadow { offset: Vec2::splat(1.5), color: Color::srgba(0.05, 0.03, 0.02, 0.95) },
            SpeechText,
        )],
    ));

    commands.spawn((
        Node {
            position_type: PositionType::Absolute,
            width: percent(100),
            top: percent(30),
            flex_direction: FlexDirection::Column,
            align_items: AlignItems::Center,
            row_gap: px(12),
            padding: UiRect::all(px(20)),
            display: Display::None,
            ..default()
        },
        BackgroundColor(Color::srgba(0.0, 0.0, 0.0, 0.75)),
        EndCard,
        children![
            (Text::new("The fire is born again."), TextFont { font_size: FontSize::Px(36.0), ..default() }, TextColor(VERB_HOVER)),
            (Text::new("End of the demo. Kiitos pelaamisesta, thanks for playing!"), TextFont { font_size: FontSize::Px(20.0), ..default() }),
        ],
    ));

    // Bottom panel: sentence line, then verbs + inventory or dialogue choices.
    let verbs: Vec<Entity> = Verb::ALL
        .iter()
        .map(|&verb| {
            commands
                .spawn((
                    Button,
                    Hovered::default(),
                    Node { width: percent(48), padding: UiRect::all(px(4)), ..default() },
                    VerbButton(verb),
                    children![(Text::new(verb.label()), TextFont { font_size: FontSize::Px(24.0), ..default() }, TextColor(VERB_COLOR))],
                    observe(move |_: On<Activate>, mut ui: ResMut<Ui>| {
                        ui.verb = if ui.verb == verb { Verb::Walk } else { verb };
                        ui.held = None;
                    }),
                ))
                .id()
        })
        .collect();

    let verb_grid = commands
        .spawn(Node { width: percent(38), flex_wrap: FlexWrap::Wrap, align_content: AlignContent::FlexStart, ..default() })
        .add_children(&verbs)
        .id();
    let inventory = commands
        .spawn((
            Node {
                flex_grow: 1.0,
                flex_wrap: FlexWrap::Wrap,
                column_gap: px(8),
                row_gap: px(8),
                align_content: AlignContent::Center,
                min_height: px(64),
                padding: UiRect::left(px(20)),
                border: UiRect::left(px(1)),
                ..default()
            },
            BorderColor::all(FRAME_GILT.with_alpha(0.45)),
            InventoryBar,
        ))
        .id();
    let verb_panel = commands
        .spawn((Node { flex_grow: 1.0, column_gap: px(20), align_items: AlignItems::Center, ..default() }, VerbPanel))
        .add_children(&[verb_grid, inventory])
        .id();
    let choices = commands
        .spawn((
            Node { flex_direction: FlexDirection::Column, row_gap: px(6), display: Display::None, ..default() },
            ChoicePanel,
        ))
        .id();
    let sentence = commands
        .spawn((
            Text::default(),
            TextFont { font_size: FontSize::Px(20.0), ..default() },
            TextColor(SENTENCE_COLOR),
            TextLayout::justify(Justify::Center),
            Node { width: percent(100), min_height: px(26), ..default() },
            SentenceText,
        ))
        .id();
    // The frame is drawn around the painting and panel; `layout` sizes and places it.
    commands.spawn((
        Node { position_type: PositionType::Absolute, ..default() },
        BorderColor::all(FRAME_WOOD),
        Pickable::IGNORE,
        Frame,
        children![(
            Node { width: percent(100), height: percent(100), border: UiRect::all(px(2)), ..default() },
            BorderColor::all(FRAME_GILT),
            Pickable::IGNORE,
        )],
    ));
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                flex_direction: FlexDirection::Column,
                padding: UiRect::axes(px(20), px(8)),
                border: UiRect::top(px(2)),
                row_gap: px(6),
                ..default()
            },
            BackgroundColor(PANEL_BG),
            BorderColor::all(FRAME_GILT),
            Panel,
        ))
        .add_children(&[sentence, verb_panel, choices]);
}

/// Fit the painting plus the panel beneath it into the window as one block, keeping the
/// painting's shape, and frame it. The scene camera draws only inside the painting.
fn layout(
    window: Single<&Window>,
    ui_scale: Res<UiScale>,
    mut camera: Single<&mut Camera, With<SceneCamera>>,
    mut panel: Single<&mut Node, (With<Panel>, Without<Frame>)>,
    mut frame: Single<&mut Node, (With<Frame>, Without<Panel>)>,
) {
    let (ww, wh) = (window.width(), window.height());
    let margin = (ww.min(wh) * 0.014).clamp(4.0, 16.0);
    let painting_aspect = ROOM_WIDTH / ROOM_HEIGHT;
    let block_aspect = painting_aspect / (1.0 + PANEL_RATIO);
    let (aw, ah) = ((ww - 2.0 * margin).max(1.0), (wh - 2.0 * margin).max(1.0));
    let (bw, bh) = if aw / ah > block_aspect { (ah * block_aspect, ah) } else { (aw, aw / block_aspect) };
    let (bx, by) = ((ww - bw) / 2.0, (wh - bh) / 2.0);
    let painting_h = bw / painting_aspect;

    let scale = window.scale_factor();
    let viewport = Viewport {
        physical_position: (Vec2::new(bx, by) * scale).round().as_uvec2(),
        physical_size: (Vec2::new(bw, painting_h) * scale).round().as_uvec2().max(UVec2::ONE),
        ..default()
    };
    if camera.viewport.as_ref().map(|v| (v.physical_position, v.physical_size))
        != Some((viewport.physical_position, viewport.physical_size))
    {
        camera.viewport = Some(viewport);
    }

    // UI units are window pixels divided by the UI scale.
    let k = ui_scale.0;
    let place = |node: &mut Node, x: f32, y: f32, w: f32, h: f32| {
        let (left, top, width, height) = (px(x / k), px(y / k), px(w / k), px(h / k));
        if node.left != left || node.top != top || node.width != width || node.height != height {
            node.left = left;
            node.top = top;
            node.width = width;
            node.height = height;
        }
    };
    place(&mut panel, bx, by + painting_h, bw, bh - painting_h);
    place(&mut frame, bx - margin, by - margin, bw + 2.0 * margin, bh + 2.0 * margin);
    let border = UiRect::all(px(margin / k));
    if frame.border != border {
        frame.border = border;
    }
}

/// The room-pixel position under a window position, if it is over the room.
fn point_in_room(camera: &Camera, transform: &GlobalTransform, pos: Vec2) -> Option<Vec2> {
    if !camera.logical_viewport_rect()?.contains(pos) {
        return None;
    }
    let world = camera.viewport_to_world_2d(transform, pos).ok()?;
    let p = world_to_room(world);
    (p.x >= 0.0 && p.x < ROOM_WIDTH && p.y >= 0.0 && p.y < ROOM_HEIGHT).then_some(p)
}

fn handle_pointer(
    mouse: Res<ButtonInput<MouseButton>>,
    touches: Res<Touches>,
    keys: Res<ButtonInput<KeyCode>>,
    window: Single<&Window>,
    camera: Single<(&Camera, &GlobalTransform), With<SceneCamera>>,
    story: Res<StoryRes>,
    game: Res<Game>,
    mut talk: ResMut<Talk>,
    mut ui: ResMut<Ui>,
    mut player: ResMut<Player>,
) {
    // On touch screens a tap is a click where the finger lands (there is no hover).
    let tap = touches.iter_just_pressed().next().map(|t| t.position());

    // Any click or tap (or Space/Enter) moves past the current line of speech.
    if talk.line.is_some() {
        let skip = [KeyCode::Space, KeyCode::Enter, KeyCode::Period];
        if mouse.just_pressed(MouseButton::Left) || tap.is_some() || keys.any_just_pressed(skip) {
            talk.line = None;
        }
        return;
    }
    if talk.dialogue.is_some() || game.0.won {
        ui.hover = None;
        return;
    }
    if keys.just_pressed(KeyCode::Escape) {
        ui.verb = Verb::Walk;
        ui.held = None;
    }

    let (camera, transform) = *camera;
    let pointer = tap.or_else(|| window.cursor_position());
    let Some(p) = pointer.and_then(|pos| point_in_room(camera, transform, pos)) else {
        ui.hover = None;
        return;
    };
    let room = story.0.room(&game.0.room);
    let hotspot = room.hotspot_at(p.x, p.y, &game.0);
    ui.hover = hotspot.map(|h| h.name.clone());

    let left = mouse.just_pressed(MouseButton::Left) || tap.is_some();
    let right = mouse.just_pressed(MouseButton::Right);
    if !left && !right {
        return;
    }
    let Some(hotspot) = hotspot else {
        if left {
            player.target = Some(Vec2::new(room.clamp_x(p.x), room.clamp_y(p.y)));
            player.pending = None;
        }
        return;
    };

    if let Some((to, x)) = &hotspot.exit {
        let (cx, _) = hotspot.rect.center();
        player.target = Some(Vec2::new(room.clamp_x(cx), room.clamp_y(player.pos.y)));
        player.pending = Some(Action::Exit { room: to.clone(), x: *x });
        return;
    }

    // Right click is a shortcut for "Look at".
    let verb = if right { Verb::Look } else { ui.verb };
    let item = if right { None } else { ui.held.clone() };
    let (x, y) = room.walk_point(hotspot, player.pos.x);
    player.target = Some(Vec2::new(x, y));
    player.pending = (verb != Verb::Walk || item.is_some()).then(|| Action::Interact {
        verb,
        item,
        target: hotspot.id.clone(),
        face_x: hotspot.rect.center().0,
    });
    ui.verb = Verb::Walk;
    ui.held = None;
}

fn hover_items(items: Query<(&ItemButton, &Hovered)>, story: Res<StoryRes>, mut ui: ResMut<Ui>) {
    for (ItemButton(id), hovered) in &items {
        if hovered.get() {
            ui.hover = story.0.item(id).map(|i| i.name.clone());
        }
    }
}

fn enter_room(story: &Story, game: &mut GameState, player: &mut Player, talk: &mut Talk, room_id: &str, x: f32) {
    let room = story.room(room_id);
    game.room = room.id.clone();
    player.pos = Vec2::new(room.clamp_x(x), (room.floor.0 + room.floor.1) / 2.0);
    player.target = None;
    player.pending = None;
    if let Some(enter) = &room.enter
        && talk.dialogue.is_none()
    {
        talk.dialogue = Some(Dialogue::new(enter.as_str()));
    }
}

fn move_player(
    time: Res<Time>,
    story: Res<StoryRes>,
    mut game: ResMut<Game>,
    mut talk: ResMut<Talk>,
    mut player: ResMut<Player>,
) {
    let Some(target) = player.target else {
        return;
    };
    let to_target = target - player.pos;
    let step = WALK_SPEED * time.delta_secs();
    if to_target.length() > step {
        player.facing_left = to_target.x < 0.0;
        player.pos += to_target.normalize() * step;
        player.walked += step;
        return;
    }
    player.pos = target;
    player.target = None;

    match player.pending.take() {
        Some(Action::Interact { verb, item, target, face_x }) => {
            player.facing_left = face_x < player.pos.x;
            talk.dialogue = story.0.interaction_node(verb, item.as_deref(), &target).map(Dialogue::new);
        }
        Some(Action::Exit { room, x }) => {
            enter_room(&story.0, &mut game.0, &mut player, &mut talk, &room, x);
        }
        None => {}
    }
}

/// Advance the dialogue until it needs the player: a line to read or a choice to make.
fn run_dialogue(story: Res<StoryRes>, mut game: ResMut<Game>, mut talk: ResMut<Talk>, mut player: ResMut<Player>) {
    if talk.dialogue.is_none() || talk.line.is_some() || !talk.choices.is_empty() {
        return;
    }
    let mut dialogue = talk.dialogue.take().unwrap();
    loop {
        match dialogue.next(&story.0, &mut game.0) {
            Step::Say { speaker, text } => {
                talk.line = Some((speaker, text));
                break;
            }
            Step::Choices(choices) => {
                talk.choices = choices;
                break;
            }
            // `talk.dialogue` is None here, so the new room's enter node doesn't interrupt.
            Step::GotoRoom { room, x } => enter_room(&story.0, &mut game.0, &mut player, &mut talk, &room, x),
            Step::Done => return,
        }
    }
    talk.dialogue = Some(dialogue);
}

fn sync_inventory(
    mut commands: Commands,
    assets: Res<AssetServer>,
    story: Res<StoryRes>,
    game: Res<Game>,
    bar: Single<Entity, With<InventoryBar>>,
) {
    commands.entity(*bar).despawn_related::<Children>().with_children(|bar| {
        for id in &game.0.inventory {
            let Some(item) = story.0.item(id) else {
                continue;
            };
            let id = id.clone();
            bar.spawn((
                Button,
                Hovered::default(),
                Node { width: px(56), height: px(56), padding: UiRect::all(px(4)), border: UiRect::all(px(2)), ..default() },
                BorderColor::all(VERB_COLOR),
                ItemButton(id.clone()),
                children![(ImageNode::new(assets.load(item.icon.clone())), Node { width: percent(100), height: percent(100), ..default() })],
                observe(move |_: On<Activate>, story: Res<StoryRes>, mut ui: ResMut<Ui>, mut talk: ResMut<Talk>| {
                    on_item_clicked(&id, &story.0, &mut ui, &mut talk);
                }),
            ));
        }
    });
}

fn on_item_clicked(id: &str, story: &Story, ui: &mut Ui, talk: &mut Talk) {
    if talk.dialogue.is_some() {
        return;
    }
    let node = match (ui.verb, ui.held.as_deref()) {
        (_, Some(held)) if held == id => {
            ui.held = None;
            ui.verb = Verb::Walk;
            return;
        }
        // Using one item on another.
        (_, Some(held)) => story.interaction_node(Verb::Use, Some(held), id),
        (Verb::Look | Verb::Take | Verb::Talk, None) => story.interaction_node(ui.verb, None, id),
        (Verb::Walk | Verb::Use, None) => {
            ui.held = Some(id.to_string());
            ui.verb = Verb::Use;
            return;
        }
    };
    talk.dialogue = node.map(Dialogue::new);
    ui.verb = Verb::Walk;
    ui.held = None;
}

fn sync_choices(mut commands: Commands, talk: Res<Talk>, panel: Single<(Entity, &mut Node), With<ChoicePanel>>) {
    let (panel, mut node) = panel.into_inner();
    set_display(&mut node, !talk.choices.is_empty());
    commands.entity(panel).despawn_related::<Children>().with_children(|panel| {
        for choice in &talk.choices {
            let choice = choice.clone();
            panel.spawn((
                Button,
                Hovered::default(),
                Node::default(),
                children![(Text::new(format!("> {}", choice.text)), TextFont { font_size: FontSize::Px(22.0), ..default() }, TextColor(CHOICE_COLOR))],
                observe(move |_: On<Activate>, story: Res<StoryRes>, mut talk: ResMut<Talk>| {
                    if talk.choices.is_empty() {
                        return;
                    }
                    talk.choices.clear();
                    if let Some(dialogue) = talk.dialogue.as_mut() {
                        dialogue.choose(&choice.target);
                    }
                    // The player says the line they picked.
                    talk.line = Some((story.0.player.clone(), choice.text.clone()));
                }),
            ));
        }
    });
}

fn draw_player(
    player: Res<Player>,
    frames: Res<PlayerFrames>,
    story: Res<StoryRes>,
    game: Res<Game>,
    mut sprite: Single<(&mut Transform, &mut Sprite), With<PlayerSprite>>,
) {
    let (transform, sprite) = &mut *sprite;
    transform.translation = room_to_world(player.pos).extend(1.0 + player.pos.y / 1000.0);
    sprite.flip_x = player.facing_left;
    let frame = if player.target.is_some() { 1 + (player.walked / STRIDE) as usize % 4 } else { 0 };
    if sprite.image != frames.0[frame] {
        sprite.image = frames.0[frame].clone();
    }
    let [r, g, b] = story.0.room(&game.0.room).light;
    sprite.color = Color::srgb_u8(r, g, b); // she takes on the room's light
}

fn set_display(node: &mut Node, show: bool) {
    let display = if show { Display::Flex } else { Display::None };
    if node.display != display {
        node.display = display;
    }
}

fn update_panel(
    story: Res<StoryRes>,
    game: Res<Game>,
    talk: Res<Talk>,
    ui: Res<Ui>,
    mut sentence: Single<&mut Text, With<SentenceText>>,
    mut verb_panel: Single<&mut Node, (With<VerbPanel>, Without<EndCard>)>,
    mut end_card: Single<&mut Node, (With<EndCard>, Without<VerbPanel>)>,
) {
    let idle = talk.dialogue.is_none() && !game.0.won;
    set_display(&mut verb_panel, idle);
    set_display(&mut end_card, game.0.won && talk.line.is_none());

    let hover = ui.hover.as_deref().unwrap_or("");
    let text = if !idle {
        String::new()
    } else if let Some(held) = &ui.held {
        let name = story.0.item(held).map_or(held.as_str(), |i| i.name.as_str());
        format!("Use {name} with {hover}")
    } else if ui.verb == Verb::Walk && hover.is_empty() {
        story.0.room(&game.0.room).name.clone()
    } else {
        format!("{} {hover}", ui.verb.label())
    };
    if sentence.0 != text {
        sentence.0 = text;
    }
}

/// Position the speech text above the speaker and colour it.
fn update_speech(
    story: Res<StoryRes>,
    game: Res<Game>,
    talk: Res<Talk>,
    player: Res<Player>,
    window: Single<&Window>,
    camera: Single<(&Camera, &GlobalTransform), With<SceneCamera>>,
    speech_box: Single<&mut Node, With<SpeechBox>>,
    speech_text: Single<(&mut Text, &mut TextColor, &mut TextFont), With<SpeechText>>,
    ui_scale: Res<UiScale>,
) {
    let mut node = speech_box.into_inner();
    let Some((speaker, line)) = &talk.line else {
        set_display(&mut node, false);
        return;
    };
    set_display(&mut node, true);

    let story = &story.0;
    let room = story.room(&game.0.room);
    // Above the player, above a hotspot named after the speaker, or at the top for voices.
    let anchor = if *speaker == story.player {
        Vec2::new(player.pos.x, player.pos.y - PLAYER_HEIGHT - 4.0)
    } else if let Some(h) = room
        .hotspots
        .iter()
        .find(|h| h.id.eq_ignore_ascii_case(speaker) && game.0.check(&h.conds))
    {
        Vec2::new(h.rect.center().0, h.rect.y - 4.0)
    } else {
        Vec2::new(ROOM_WIDTH / 2.0, 30.0)
    };

    let (camera, transform) = *camera;
    let Ok(screen) = camera.world_to_viewport(transform, room_to_world(anchor).extend(0.0)) else {
        return;
    };
    // Computed in window pixels, then converted to UI units (window pixels / UiScale).
    let k = ui_scale.0;
    // Keep the speech inside the painting.
    let painting = camera.logical_viewport_rect().unwrap_or(Rect::new(0.0, 0.0, window.width(), window.height()));
    let width = (painting.width() * 0.5).clamp(220.0, 520.0);
    let left = (screen.x - width / 2.0).clamp(painting.min.x + 8.0, (painting.max.x - width - 8.0).max(painting.min.x + 8.0));
    node.left = px(left / k);
    node.bottom = px((window.height() - screen.y.max(60.0)) / k);
    node.width = px(width / k);
    node.justify_content = JustifyContent::Center;

    let (mut text, mut color, mut font) = speech_text.into_inner();
    let rgb = story.characters.get(speaker).map_or([255, 255, 255], |c| c.color);
    color.0 = Color::srgb_u8(rgb[0], rgb[1], rgb[2]);
    let size = (painting.height() / ROOM_HEIGHT * 6.0).clamp(15.0, 28.0) / k;
    if font.font_size != FontSize::Px(size) {
        font.font_size = FontSize::Px(size);
    }
    if text.0 != *line {
        text.0 = line.clone();
    }
}

fn style_buttons(
    ui: Res<Ui>,
    verbs: Query<(&VerbButton, &Hovered, &Children)>,
    items: Query<(&ItemButton, &Hovered, &mut BorderColor)>,
    choices: Query<(&Hovered, &Children), (With<Button>, Without<VerbButton>, Without<ItemButton>)>,
    mut texts: Query<&mut TextColor>,
) {
    for (VerbButton(verb), hovered, children) in &verbs {
        if let Ok(mut color) = texts.get_mut(children[0]) {
            color.0 = if hovered.get() || ui.verb == *verb { VERB_HOVER } else { VERB_COLOR };
        }
    }
    for (ItemButton(id), hovered, mut border) in items {
        let active = hovered.get() || ui.held.as_deref() == Some(id);
        border.set_all(if active { VERB_HOVER } else { VERB_COLOR });
    }
    for (hovered, children) in &choices {
        if let Ok(mut color) = texts.get_mut(children[0]) {
            color.0 = if hovered.get() { VERB_HOVER } else { CHOICE_COLOR };
        }
    }
}

fn apply_font(font: Res<GameFont>, mut texts: Query<&mut TextFont, Added<TextFont>>) {
    for mut text in &mut texts {
        text.font = font.0.clone().into();
    }
}

fn toggle_sound(keys: Res<ButtonInput<KeyCode>>, mut sound: ResMut<SoundOn>) {
    if keys.just_pressed(KeyCode::KeyM) {
        sound.0 = !sound.0;
    }
}

/// Crossfade to the current room's music (or the ending music once the game is won).
fn play_music(
    mut commands: Commands,
    time: Res<Time>,
    assets: Res<AssetServer>,
    story: Res<StoryRes>,
    game: Res<Game>,
    talk: Res<Talk>,
    sound: Res<SoundOn>,
    mut tracks: Query<(Entity, &mut MusicTrack, Option<&mut AudioSink>)>,
) {
    let wanted = if game.0.won && talk.line.is_none() {
        story.0.ending_music.as_ref()
    } else {
        story.0.room(&game.0.room).music.as_ref()
    };
    if let Some(path) = wanted
        && !tracks.iter().any(|(_, t, _)| &t.path == path && !t.fading_out)
    {
        commands.spawn((
            AudioPlayer::new(assets.load(path.clone())),
            PlaybackSettings::LOOP.with_volume(Volume::Linear(0.0)),
            MusicTrack { path: path.clone(), volume: 0.0, fading_out: false },
        ));
    }
    let step = MUSIC_FADE * time.delta_secs();
    for (entity, mut track, sink) in &mut tracks {
        if Some(&track.path) != wanted {
            track.fading_out = true;
        }
        let target = if track.fading_out || !sound.0 { 0.0 } else { MUSIC_VOLUME };
        track.volume += (target - track.volume).clamp(-step, step);
        if let Some(mut sink) = sink {
            sink.set_volume(Volume::Linear(track.volume));
        }
        if track.fading_out && track.volume <= 0.0 {
            commands.entity(entity).despawn();
        }
    }
}

/// Babble syllables while a line is on screen, in the speaker's voice.
fn play_babble(
    mut commands: Commands,
    time: Res<Time>,
    talk: Res<Talk>,
    voices: Res<VoiceBank>,
    sound: Res<SoundOn>,
    mut babble: ResMut<Babble>,
) {
    let now = time.elapsed_secs();
    if talk.line != babble.line {
        let babble = &mut *babble;
        babble.line = talk.line.clone();
        babble.started = now;
        babble.queue.clear();
        if let Some((speaker, text)) = &talk.line
            && let Some((_, rate)) = voices.0.get(speaker)
        {
            babble.queue = babble_schedule(text, *rate, &mut babble.rng).into();
        }
    }
    let Some((speaker, _)) = &babble.line else {
        return;
    };
    let Some((clips, _)) = voices.0.get(speaker) else {
        return;
    };
    let elapsed = now - babble.started;
    while babble.queue.front().is_some_and(|(at, _)| *at <= elapsed) {
        let (_, speed) = babble.queue.pop_front().unwrap();
        if sound.0 {
            let clip = clips[(next_random(&mut babble.rng) * clips.len() as f32) as usize % clips.len()].clone();
            commands.spawn((
                AudioPlayer::new(clip),
                PlaybackSettings::DESPAWN.with_speed(speed).with_volume(Volume::Linear(VOICE_VOLUME)),
            ));
        }
    }
}

/// When each syllable plays and at what pitch: roughly one per three letters,
/// pausing at punctuation and rising at the end of a question.
fn babble_schedule(text: &str, rate: f32, rng: &mut u64) -> Vec<(f32, f32)> {
    const MAX_SYLLABLES: usize = 40;
    let mut out: Vec<(f32, f32)> = Vec::new();
    let mut t = 0.0;
    for word in text.split_whitespace() {
        // Stage directions like "(singing)" aren't spoken.
        if word.starts_with('(') || word.ends_with(')') {
            continue;
        }
        let letters = word.chars().filter(|c| c.is_alphabetic()).count();
        if letters == 0 {
            continue;
        }
        for _ in 0..letters.div_ceil(3) {
            let speed = 0.92 + 0.2 * next_random(rng);
            out.push((t, speed));
            t += rate * (0.85 + 0.3 * next_random(rng));
        }
        match word.chars().last() {
            Some('?') => {
                if let Some(last) = out.last_mut() {
                    last.1 *= 1.25;
                }
                t += rate * 2.5;
            }
            Some('.' | '!') => t += rate * 2.5,
            Some(',' | ';' | ':') => t += rate * 1.5,
            _ => {}
        }
        if out.len() >= MAX_SYLLABLES {
            break;
        }
    }
    out
}

/// xorshift: a random number in [0, 1).
fn next_random(state: &mut u64) -> f32 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    (*state >> 40) as f32 / (1u64 << 24) as f32
}

/// Shrink the interface on small screens (phones) and grow it on big ones.
/// Sizes in the UI are designed for a 1280x720 window.
fn scale_ui(window: Single<&Window>, mut ui_scale: ResMut<UiScale>) {
    let scale = (window.width() / 1280.0).min(window.height() / 720.0).clamp(0.6, 1.6);
    if (ui_scale.0 - scale).abs() > 0.01 {
        ui_scale.0 = scale;
    }
}

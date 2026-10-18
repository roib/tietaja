//! What a room looks like and how it moves: the painting, a sky drifting behind it, the
//! hotspot sprites (characters breathe), and the room's effects: birds crossing the sky,
//! glints on water, dust in sunbeams, falling leaves, chimney smoke, firelight.

use bevy::{prelude::*, sprite::Anchor};

use crate::story::{Effect, EffectKind, Rect as RoomRect, ROOM_HEIGHT, ROOM_WIDTH};
use crate::{Game, StoryRes, next_random, room_to_world};

/// Room units per second the sky drifts left.
const SKY_SPEED: f32 = 1.6;

pub struct SceneryPlugin;

impl Plugin for SceneryPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<ShownRoom>().add_systems(Startup, (load_effect_art, preload_room_art)).add_systems(
            Update,
            (sync_scenery, (drift_sky, breathe, animate_sprites, animate_effects)).chain(),
        );
    }
}

/// The room currently on screen, which lags the game's room while its art loads.
#[derive(Resource, Default)]
pub struct ShownRoom(pub Option<String>);

/// Everything shown for the current room; despawned when the room changes.
#[derive(Component)]
struct RoomEntity;

#[derive(Component)]
struct HotspotSprite;

/// One of the two side-by-side copies of the room's wide sky.
#[derive(Component)]
struct SkyLayer {
    copy: f32,
}

/// A hotspot sprite that plays through its frames.
#[derive(Component)]
struct Animated {
    frames: Vec<Handle<Image>>,
    fps: f32,
}

#[derive(Component)]
struct Breathing {
    base: Vec3,
    phase: f32,
}

/// The room's effect number `index`, which owns that effect's particles.
#[derive(Component)]
struct Emitter {
    index: usize,
    kind: EffectKind,
    rect: RoomRect,
    /// Seconds until the next flock of birds.
    timer: f32,
}

#[derive(Component)]
struct Particle {
    pos: Vec2,
    vel: Vec2,
    age: f32,
    phase: f32,
    /// For sparkles: which glint this is, to move on after each one.
    cycle: u32,
}

#[derive(Resource, Clone)]
struct EffectArt {
    sparkle: Handle<Image>,
    mote: Handle<Image>,
    smoke: Handle<Image>,
    spark: Handle<Image>,
    leaf: Handle<Image>,
    glow: Handle<Image>,
    bird: [Handle<Image>; 2],
}

/// Every room's art, loaded at startup and held for the whole game. Otherwise a room's
/// images would only be fetched on entering it (and dropped on leaving), showing the bare
/// wall until they arrive.
#[derive(Resource)]
struct RoomArt(#[allow(dead_code)] Vec<Handle<Image>>);

fn preload_room_art(mut commands: Commands, assets: Res<AssetServer>, story: Res<StoryRes>) {
    let story = &story.0;
    let paths = story.rooms.iter().flat_map(|room| {
        std::iter::once(room.background.clone())
            .chain(room.sky.clone())
            .chain(room.hotspots.iter().flat_map(|h| h.sprite_frames()))
    });
    let icons = story.items.iter().map(|item| item.icon.clone());
    commands.insert_resource(RoomArt(paths.chain(icons).map(|path| assets.load(path)).collect()));
}

/// Loaded, or failed to load (so a missing file doesn't hold up the game forever).
fn ready(assets: &AssetServer, path: &str) -> bool {
    let state = assets.load_state(&assets.load::<Image>(path.to_owned()));
    state.is_loaded() || state.is_failed()
}

#[allow(clippy::too_many_arguments)]
fn sync_scenery(
    mut commands: Commands,
    assets: Res<AssetServer>,
    story: Res<StoryRes>,
    game: Res<Game>,
    mut shown_room: ResMut<ShownRoom>,
    mut rng: Local<u64>,
    room_entities: Query<Entity, With<RoomEntity>>,
    hotspot_sprites: Query<Entity, With<HotspotSprite>>,
    emitters: Query<(Entity, &Emitter)>,
    art: Res<EffectArt>,
) {
    if *rng == 0 {
        *rng = 0x2545_F491_4F6C_DD1D;
    }
    let room = story.0.room(&game.0.room);
    let new_room = shown_room.0.as_deref() != Some(room.id.as_str());
    if !new_room && !game.is_changed() {
        return;
    }
    // Keep showing the old room until the new one's art has arrived, rather than flashing
    // the bare wall in between.
    if new_room {
        let mut paths = std::iter::once(room.background.clone())
            .chain(room.sky.clone())
            .chain(room.hotspots.iter().flat_map(|h| h.sprite_frames()));
        if !paths.all(|path| ready(&assets, &path)) {
            return;
        }
    }

    if new_room {
        for entity in &room_entities {
            commands.entity(entity).despawn();
        }
        shown_room.0 = Some(room.id.clone());
        // The painting (with its sky cut out) and the sky drifting behind it. Art is painted
        // at a higher resolution than the room, so everything is drawn at room size.
        commands.spawn((
            Sprite { custom_size: Some(Vec2::new(ROOM_WIDTH, ROOM_HEIGHT)), ..Sprite::from_image(assets.load(room.background.clone())) },
            Transform::default(),
            RoomEntity,
        ));
        if let Some(sky) = &room.sky {
            for copy in [0.0, 1.0] {
                commands.spawn((
                    Sprite { custom_size: Some(Vec2::new(ROOM_WIDTH * 2.0, ROOM_HEIGHT)), ..Sprite::from_image(assets.load(sky.clone())) },
                    Transform::from_xyz(0.0, 0.0, -1.0),
                    SkyLayer { copy },
                    RoomEntity,
                ));
            }
        }
    } else {
        for entity in &hotspot_sprites {
            commands.entity(entity).despawn();
        }
    }

    for hotspot in room.hotspots.iter().filter(|h| game.0.check(&h.conds)) {
        let frames: Vec<Handle<Image>> = hotspot.sprite_frames().into_iter().map(|path| assets.load(path)).collect();
        let Some(first) = frames.first().cloned() else {
            continue;
        };
        let r = hotspot.rect;
        let feet = room_to_world(Vec2::new(r.x + r.w / 2.0, r.y + r.h)).extend(1.0 + (r.y + r.h) / 1000.0);
        let [lr, lg, lb] = room.light;
        let mut entity = commands.spawn((
            Sprite {
                custom_size: Some(Vec2::new(r.w, r.h)),
                color: Color::srgb_u8(lr, lg, lb), // in the room's light
                ..Sprite::from_image(first)
            },
            Anchor::BOTTOM_CENTER,
            Transform::from_translation(feet),
            HotspotSprite,
            RoomEntity,
        ));
        if let Some((_, fps)) = hotspot.frames {
            entity.insert(Animated { frames, fps });
        }
        // Characters (hotspots named after someone who speaks) breathe gently.
        if story.0.characters.keys().any(|name| name.eq_ignore_ascii_case(&hotspot.id)) {
            entity.insert(Breathing { base: feet, phase: next_random(&mut rng) * 6.28 });
        }
    }

    // Effects come and go with their conditions (smoke only once the fire is lit).
    for (index, effect) in room.effects.iter().enumerate() {
        let active = game.0.check(&effect.conds);
        let existing = if new_room { None } else { emitters.iter().find(|(_, e)| e.index == index).map(|(entity, _)| entity) };
        match (active, existing) {
            (true, None) => spawn_effect(&mut commands, &art, index, effect, &mut rng),
            (false, Some(entity)) => {
                commands.entity(entity).despawn();
            }
            _ => {}
        }
    }
}

fn load_effect_art(mut commands: Commands, assets: Res<AssetServer>) {
    commands.insert_resource(EffectArt {
            sparkle: assets.load("effects/sparkle.png"),
            mote: assets.load("effects/mote.png"),
            smoke: assets.load("effects/smoke.png"),
        spark: assets.load("effects/spark.png"),
            leaf: assets.load("effects/leaf.png"),
            glow: assets.load("intro/ember.png"),
            bird: [assets.load("effects/bird_0.png"), assets.load("effects/bird_1.png")],
    });
}

impl EffectArt {
    fn image(&self, kind: EffectKind) -> Handle<Image> {
        match kind {
            EffectKind::Sparkles => self.sparkle.clone(),
            EffectKind::Motes => self.mote.clone(),
            EffectKind::Smoke => self.smoke.clone(),
            EffectKind::Sparks => self.spark.clone(),
            EffectKind::Leaves => self.leaf.clone(),
            EffectKind::Glow => self.glow.clone(),
            EffectKind::Birds => self.bird[0].clone(),
        }
    }
}

/// Size in room units, and depth: birds fly behind the trees, dust floats in front of everything.
fn look(kind: EffectKind, rect: RoomRect) -> (Vec2, f32) {
    match kind {
        EffectKind::Sparkles => (Vec2::splat(3.0), 0.5),
        EffectKind::Motes => (Vec2::splat(1.6), 2.5),
        EffectKind::Smoke => (Vec2::splat(5.0), 0.6),
        EffectKind::Sparks => (Vec2::splat(1.1), 1.25),
        EffectKind::Leaves => (Vec2::new(2.6, 2.0), 2.4),
        EffectKind::Glow => (Vec2::new(rect.w, rect.h) * 1.5, 1.2),
        EffectKind::Birds => (Vec2::new(5.0, 2.5), -0.5),
    }
}

fn spawn_effect(commands: &mut Commands, art: &EffectArt, index: usize, effect: &Effect, rng: &mut u64) {
    let (size, _) = look(effect.kind, effect.rect);
    let emitter = commands
        .spawn((
            Emitter { index, kind: effect.kind, rect: effect.rect, timer: 2.0 + next_random(rng) * 4.0 },
            Transform::default(),
            Visibility::default(),
            RoomEntity,
        ))
        .id();
    // Birds arrive in flocks over time; everything else starts with all its particles.
    if effect.kind == EffectKind::Birds {
        return;
    }
    for i in 0..effect.count.max(1) {
        let r = effect.rect;
        let pos = Vec2::new(r.x + next_random(rng) * r.w, r.y + next_random(rng) * r.h);
        // Smoke puffs and sparks are staggered along their rise so the stream is continuous.
        let age = match effect.kind {
            EffectKind::Smoke => i as f32 / effect.count as f32 * SMOKE_LIFE,
            EffectKind::Sparks => i as f32 / effect.count as f32 * SPARK_LIFE,
            _ => 0.0,
        };
        commands.spawn((
            Sprite { custom_size: Some(size), color: Color::NONE, ..Sprite::from_image(art.image(effect.kind)) },
            Transform::from_translation(room_to_world(pos).extend(0.0)),
            Particle { pos, vel: Vec2::ZERO, age, phase: next_random(rng) * 6.28, cycle: 0 },
            ChildOf(emitter),
        ));
    }
}

const SMOKE_LIFE: f32 = 5.0;
const SPARK_LIFE: f32 = 1.6;

fn drift_sky(time: Res<Time>, mut skies: Query<(&SkyLayer, &mut Transform)>) {
    let width = ROOM_WIDTH * 2.0;
    let offset = (time.elapsed_secs() * SKY_SPEED) % width;
    for (layer, mut transform) in &mut skies {
        // Two copies side by side, both sliding left; each wraps around behind the other.
        let left = -ROOM_WIDTH / 2.0 - offset + layer.copy * width;
        transform.translation.x = left + width / 2.0;
    }
}

fn breathe(time: Res<Time>, mut sprites: Query<(&Breathing, &mut Transform)>) {
    let t = time.elapsed_secs();
    for (breathing, mut transform) in &mut sprites {
        transform.translation = breathing.base;
        transform.scale = Vec3::new(1.0, 1.0 + 0.012 * (t * 1.7 + breathing.phase).sin(), 1.0);
    }
}

fn animate_effects(
    mut commands: Commands,
    time: Res<Time>,
    art: Res<EffectArt>,
    mut rng: Local<u64>,
    mut emitters: Query<(Entity, &mut Emitter, Option<&Children>)>,
    mut particles: Query<(&mut Particle, &mut Transform, &mut Sprite)>,
) {
    if *rng == 0 {
        *rng = 0x9E37_79B9_7F4A_7C15;
    }
    let dt = time.delta_secs();
    let t = time.elapsed_secs();
    for (emitter_entity, mut emitter, children) in &mut emitters {
        let r = emitter.rect;
        let (size, depth) = look(emitter.kind, r);

        if emitter.kind == EffectKind::Birds {
            emitter.timer -= dt;
            if emitter.timer <= 0.0 {
                emitter.timer = 9.0 + next_random(&mut rng) * 12.0;
                let from_left = next_random(&mut rng) < 0.5;
                let speed = (16.0 + next_random(&mut rng) * 10.0) * if from_left { 1.0 } else { -1.0 };
                let y = r.y + next_random(&mut rng) * r.h;
                let flock = 3 + (next_random(&mut rng) * 4.0) as usize;
                for i in 0..flock {
                    // A loose V: each bird a little behind and to the side of the one before.
                    let behind = i as f32 * 4.5 + next_random(&mut rng) * 2.0;
                    let x = if from_left { r.x - 6.0 - behind } else { r.x + r.w + 6.0 + behind };
                    let pos = Vec2::new(x, y + (i as f32 * 1.7) * if i % 2 == 0 { 1.0 } else { -1.0 });
                    commands.spawn((
                        Sprite { custom_size: Some(size), flip_x: !from_left, ..Sprite::from_image(art.bird[0].clone()) },
                        Transform::from_translation(room_to_world(pos).extend(depth)),
                        Particle { pos, vel: Vec2::new(speed, 0.0), age: 0.0, phase: next_random(&mut rng) * 6.28, cycle: 0 },
                        ChildOf(emitter_entity),
                    ));
                }
            }
        }

        let Some(children) = children else {
            continue;
        };
        for &child in children {
            let Ok((p, mut transform, mut sprite)) = particles.get_mut(child) else {
                continue;
            };
            let p = p.into_inner();
            p.age += dt;
            let mut alpha = 1.0;
            let mut scale = 1.0;
            let mut rotation = 0.0;
            match emitter.kind {
                EffectKind::Sparkles => {
                    // A glint on the water: a quick flash, then reappear somewhere else.
                    let cycle = 1.6;
                    let glints = (p.age + p.phase) / cycle;
                    if glints as u32 != p.cycle {
                        p.cycle = glints as u32;
                        p.pos = Vec2::new(r.x + next_random(&mut rng) * r.w, r.y + next_random(&mut rng) * r.h);
                    }
                    let k = glints.fract();
                    alpha = (1.0 - (k * 2.0 - 1.0).abs()).powi(6);
                    scale = 0.6 + alpha * 0.6;
                }
                EffectKind::Motes => {
                    // Dust turning slowly in a sunbeam.
                    p.pos += Vec2::new((t * 0.3 + p.phase).sin() * 0.8, -0.4 + (t * 0.5 + p.phase * 2.0).cos() * 0.5) * dt;
                    wrap(&mut p.pos, r);
                    alpha = 0.25 + 0.35 * (t * 0.8 + p.phase).sin().max(0.0);
                }
                EffectKind::Leaves => {
                    // Drifting down, swaying and turning.
                    p.pos.y += 5.0 * dt;
                    p.pos.x += (t * 1.3 + p.phase).sin() * 6.0 * dt;
                    rotation = (t * 2.0 + p.phase).sin() * 0.9;
                    if p.pos.y > r.y + r.h + 20.0 {
                        p.pos = Vec2::new(r.x + next_random(&mut rng) * r.w, r.y);
                    }
                    alpha = (1.0 - ((p.pos.y - (r.y + r.h)) / 20.0).max(0.0)).clamp(0.0, 1.0);
                }
                EffectKind::Smoke => {
                    // Puffs rise from the chimney, swell, lean with the breeze and fade.
                    if p.age > SMOKE_LIFE {
                        p.age -= SMOKE_LIFE;
                    }
                    let k = p.age / SMOKE_LIFE;
                    p.pos = Vec2::new(r.x + r.w / 2.0 + k * k * 14.0 + (p.age * 1.3 + p.phase).sin() * 1.0, r.y + r.h - k * 34.0);
                    scale = 0.7 + k * 3.2;
                    alpha = 0.8 * (k * 6.0).min(1.0) * (1.0 - k).powf(0.8);
                }
                EffectKind::Sparks => {
                    // Embers spat up from the fire, rising, wavering and burning out.
                    if p.age > SPARK_LIFE {
                        p.age -= SPARK_LIFE;
                        p.phase = next_random(&mut rng) * 6.28;
                        p.pos = Vec2::new(r.x + r.w * (0.3 + 0.4 * next_random(&mut rng)), r.y + r.h);
                    }
                    let k = p.age / SPARK_LIFE;
                    let rise = 7.0 + 5.0 * (p.phase * 3.7).sin().abs();
                    p.pos.y = r.y + r.h - k * r.h * (rise / 12.0);
                    p.pos.x += (t * 6.0 + p.phase).sin() * 4.0 * dt + 1.2 * dt;
                    alpha = (1.0 - k).powf(1.5) * (0.75 + 0.25 * (t * 30.0 + p.phase).sin());
                    scale = 1.0 - 0.5 * k;
                    transform.translation = room_to_world(p.pos).extend(depth);
                    transform.scale = Vec3::splat(scale);
                    sprite.color = Color::srgba(1.0, 0.55 + 0.35 * (1.0 - k), 0.2, alpha); // white-hot to deep orange
                    continue;
                }
                EffectKind::Glow => {
                    // Firelight breathing over the flames.
                    p.pos = Vec2::new(r.x + r.w / 2.0, r.y + r.h / 2.0);
                    alpha = 0.42 + 0.12 * (t * 9.0).sin() + 0.08 * (t * 23.0 + 1.3).sin();
                    scale = 1.0 + 0.05 * (t * 11.0).sin();
                }
                EffectKind::Birds => {
                    p.pos += p.vel * dt;
                    p.pos.y += (t * 0.8 + p.phase).sin() * 0.6 * dt;
                    let flap = ((t * 5.0 + p.phase) as i32 % 2) as usize;
                    sprite.image = art.bird[flap].clone();
                    if p.pos.x < r.x - 60.0 || p.pos.x > r.x + r.w + 60.0 {
                        commands.entity(child).despawn();
                    }
                }
            }
            transform.translation = room_to_world(p.pos).extend(depth);
            transform.scale = Vec3::splat(scale);
            transform.rotation = Quat::from_rotation_z(rotation);
            sprite.color = Color::srgba(1.0, 1.0, 1.0, alpha);
        }
    }
}

/// Keep a drifting particle inside its area by wrapping around the edges.
fn wrap(pos: &mut Vec2, r: RoomRect) {
    if pos.x < r.x {
        pos.x += r.w;
    } else if pos.x > r.x + r.w {
        pos.x -= r.w;
    }
    if pos.y < r.y {
        pos.y += r.h;
    } else if pos.y > r.y + r.h {
        pos.y -= r.h;
    }
}

fn animate_sprites(time: Res<Time>, mut sprites: Query<(&Animated, &mut Sprite)>) {
    for (animated, mut sprite) in &mut sprites {
        let frame = (time.elapsed_secs() * animated.fps) as usize % animated.frames.len();
        if sprite.image != animated.frames[frame] {
            sprite.image = animated.frames[frame].clone();
        }
    }
}

//! The story: parsing `assets/story.txt` and running its dialogue.
//! Pure Rust with no Bevy types, so it can be tested directly.

use std::collections::{HashMap, HashSet};

pub const ROOM_WIDTH: f32 = 320.0;
pub const ROOM_HEIGHT: f32 = 144.0;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Rect {
    pub x: f32,
    pub y: f32,
    pub w: f32,
    pub h: f32,
}

impl Rect {
    pub fn contains(&self, x: f32, y: f32) -> bool {
        x >= self.x && x < self.x + self.w && y >= self.y && y < self.y + self.h
    }

    pub fn center(&self) -> (f32, f32) {
        (self.x + self.w / 2.0, self.y + self.h / 2.0)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Cond {
    pub flag: String,
    pub negate: bool,
}

#[derive(Clone, Debug)]
pub struct Character {
    pub color: [u8; 3],
    pub voice: Option<Voice>,
}

/// Babble voice: syllable clips in `dir` (0.ogg, 1.ogg, ...), played every `rate` seconds.
#[derive(Clone, Debug)]
pub struct Voice {
    pub dir: String,
    pub rate: f32,
}

pub const VOICE_SYLLABLES: usize = 6;

#[derive(Clone, Debug)]
pub struct Item {
    pub id: String,
    pub name: String,
    pub icon: String,
}

#[derive(Clone, Debug)]
pub struct Hotspot {
    pub id: String,
    pub name: String,
    pub rect: Rect,
    pub sprite: Option<String>,
    /// An animated sprite: (frame count, frames per second). Its path has `{}` where the
    /// frame number goes.
    pub frames: Option<(u32, f32)>,
    pub conds: Vec<Cond>,
    /// Exits lead to (room, x) instead of running interaction nodes.
    pub exit: Option<(String, f32)>,
}

/// Something alive in a room: birds crossing the sky, glints on water, drifting leaves...
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EffectKind {
    Birds,
    Sparkles,
    Motes,
    Leaves,
    Smoke,
    Sparks,
    Glow,
}

impl EffectKind {
    fn parse(name: &str) -> Option<Self> {
        Some(match name {
            "birds" => Self::Birds,
            "sparkles" => Self::Sparkles,
            "motes" => Self::Motes,
            "leaves" => Self::Leaves,
            "smoke" => Self::Smoke,
            "sparks" => Self::Sparks,
            "glow" => Self::Glow,
            _ => return None,
        })
    }
}

#[derive(Clone, Debug)]
pub struct Effect {
    pub kind: EffectKind,
    /// The area the effect lives in (room pixels).
    pub rect: Rect,
    pub count: u32,
    pub conds: Vec<Cond>,
}

#[derive(Clone, Debug)]
pub struct Room {
    pub id: String,
    pub name: String,
    pub background: String,
    /// Range of y values the player's feet can stand on.
    pub floor: (f32, f32),
    pub enter: Option<String>,
    pub music: Option<String>,
    /// A wide sky image that drifts slowly behind the room (whose own sky is transparent).
    pub sky: Option<String>,
    /// The colour of the room's light, which tints the characters and objects in it.
    pub light: [u8; 3],
    pub effects: Vec<Effect>,
    pub hotspots: Vec<Hotspot>,
}

impl Hotspot {
    /// The image files of the hotspot's sprite: one, or each frame of an animation.
    pub fn sprite_frames(&self) -> Vec<String> {
        match (&self.sprite, self.frames) {
            (Some(path), Some((count, _))) => (0..count).map(|i| path.replace("{}", &i.to_string())).collect(),
            (Some(path), None) => vec![path.clone()],
            (None, _) => Vec::new(),
        }
    }
}

impl Room {
    /// Topmost visible hotspot under a point. Later hotspots are drawn on top.
    pub fn hotspot_at(&self, x: f32, y: f32, state: &GameState) -> Option<&Hotspot> {
        self.hotspots
            .iter()
            .rev()
            .find(|h| h.rect.contains(x, y) && state.check(&h.conds))
    }

    /// Where the player stands to interact with a hotspot: beside it, on the side they come from.
    pub fn walk_point(&self, hotspot: &Hotspot, from_x: f32) -> (f32, f32) {
        const GAP: f32 = 8.0;
        let r = hotspot.rect;
        let x = if from_x < r.x {
            r.x - GAP
        } else if from_x > r.x + r.w {
            r.x + r.w + GAP
        } else {
            from_x
        };
        (self.clamp_x(x), self.clamp_y(r.y + r.h))
    }

    pub fn clamp_x(&self, x: f32) -> f32 {
        x.clamp(6.0, ROOM_WIDTH - 6.0)
    }

    pub fn clamp_y(&self, y: f32) -> f32 {
        y.clamp(self.floor.0, self.floor.1)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum LineKind {
    Say { speaker: String, text: String },
    Choice { text: String, target: String },
    Jump(String),
    Set(String),
    Clear(String),
    Give(String),
    Remove(String),
    Goto(String, f32),
    End,
    Win,
}

#[derive(Clone, Debug)]
pub struct Line {
    pub conds: Vec<Cond>,
    pub kind: LineKind,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Verb {
    Walk,
    Look,
    Take,
    Use,
    Talk,
}

impl Verb {
    pub const ALL: [Verb; 4] = [Verb::Look, Verb::Take, Verb::Use, Verb::Talk];

    pub fn key(self) -> &'static str {
        match self {
            Verb::Walk => "walk",
            Verb::Look => "look",
            Verb::Take => "take",
            Verb::Use => "use",
            Verb::Talk => "talk",
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Verb::Walk => "Walk to",
            Verb::Look => "Look at",
            Verb::Take => "Pick up",
            Verb::Use => "Use",
            Verb::Talk => "Talk to",
        }
    }
}

#[derive(Debug)]
pub struct Story {
    /// The tale's name, shown on the menu.
    pub title: Option<String>,
    /// Shown once the tale is won.
    pub ending: Option<String>,
    /// The character the player controls; their lines appear above the player.
    pub player: String,
    pub start: (String, f32),
    pub intro: Option<String>,
    pub ending_music: Option<String>,
    pub characters: HashMap<String, Character>,
    pub items: Vec<Item>,
    pub rooms: Vec<Room>,
    pub nodes: HashMap<String, Vec<Line>>,
}

impl Story {
    pub fn room(&self, id: &str) -> &Room {
        self.rooms.iter().find(|r| r.id == id).expect("room ids are validated on parse")
    }

    pub fn item(&self, id: &str) -> Option<&Item> {
        self.items.iter().find(|i| i.id == id)
    }

    /// Which node to run when the player applies a verb (and maybe an item) to a target.
    pub fn interaction_node(&self, verb: Verb, item: Option<&str>, target: &str) -> Option<String> {
        let (specific, fallback) = match item {
            Some(item) => (format!("use_{item}_{target}"), "default_use_item".to_string()),
            None => (format!("{}_{target}", verb.key()), format!("default_{}", verb.key())),
        };
        [specific, fallback].into_iter().find(|n| self.nodes.contains_key(n))
    }

    pub fn parse(src: &str) -> Result<Story, String> {
        let mut story = Story {
            title: None,
            ending: None,
            player: "Player".to_string(),
            start: (String::new(), 0.0),
            intro: None,
            ending_music: None,
            characters: HashMap::new(),
            items: Vec::new(),
            rooms: Vec::new(),
            nodes: HashMap::new(),
        };
        // Which block indented lines belong to.
        enum Block {
            None,
            Room,
            Node(String),
        }
        let mut block = Block::None;

        for (i, raw) in src.lines().enumerate() {
            let err = |msg: &str| format!("story.txt line {}: {msg}\n  {}", i + 1, raw.trim());
            let line = raw.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            let indented = raw.starts_with(' ') || raw.starts_with('\t');

            if !indented {
                let (keyword, rest) = line.split_once(' ').unwrap_or((line, ""));
                let rest = rest.trim();
                block = Block::None;
                match keyword {
                    "start:" => {
                        let (room, x) = rest.split_once(' ').ok_or_else(|| err("expected `start: <room> <x>`"))?;
                        story.start = (room.to_string(), parse_num(x).map_err(|e| err(&e))?);
                    }
                    "intro:" => story.intro = Some(rest.to_string()),
                    "title:" => story.title = Some(rest.to_string()),
                    "ending:" => story.ending = Some(rest.to_string()),
                    "player:" => story.player = rest.to_string(),
                    "ending_music:" => story.ending_music = Some(rest.to_string()),
                    "character" => {
                        let usage = "expected `character Name: #rrggbb [| voice <dir> <seconds per syllable>]`";
                        let (name, rest) = rest.split_once(':').ok_or_else(|| err(usage))?;
                        let (color, voice) = match rest.split_once('|') {
                            Some((color, voice)) => {
                                let mut words = voice.split_whitespace();
                                let (Some("voice"), Some(dir), Some(rate), None) =
                                    (words.next(), words.next(), words.next(), words.next())
                                else {
                                    return Err(err(usage));
                                };
                                let rate = parse_num(rate).map_err(|e| err(&e))?;
                                (color, Some(Voice { dir: dir.to_string(), rate }))
                            }
                            None => (rest, None),
                        };
                        let color = parse_color(color.trim()).map_err(|e| err(&e))?;
                        story.characters.insert(name.trim().to_string(), Character { color, voice });
                    }
                    "item" => {
                        let (id, rest) = rest.split_once(':').ok_or_else(|| err("expected `item id: Name | icon`"))?;
                        let (name, icon) = rest.split_once('|').ok_or_else(|| err("expected `item id: Name | icon`"))?;
                        story.items.push(Item {
                            id: id.trim().to_string(),
                            name: name.trim().to_string(),
                            icon: icon.trim().to_string(),
                        });
                    }
                    "room" => {
                        let (id, name) = rest.split_once(':').ok_or_else(|| err("expected `room id: Name`"))?;
                        story.rooms.push(Room {
                            id: id.trim().to_string(),
                            name: name.trim().to_string(),
                            background: String::new(),
                            floor: (100.0, 140.0),
                            enter: None,
                            music: None,
                            sky: None,
                            light: [255, 255, 255],
                            effects: Vec::new(),
                            hotspots: Vec::new(),
                        });
                        block = Block::Room;
                    }
                    "node" => {
                        if story.nodes.insert(rest.to_string(), Vec::new()).is_some() {
                            return Err(err("duplicate node name"));
                        }
                        block = Block::Node(rest.to_string());
                    }
                    _ => return Err(err("unknown keyword")),
                }
                continue;
            }

            match &block {
                Block::None => return Err(err("indented line outside a room or node")),
                Block::Room => {
                    let room = story.rooms.last_mut().unwrap();
                    parse_room_line(room, line).map_err(|e| err(&e))?;
                }
                Block::Node(name) => {
                    let parsed = parse_node_line(line).map_err(|e| err(&e))?;
                    story.nodes.get_mut(name).unwrap().push(parsed);
                }
            }
        }

        story.validate()?;
        Ok(story)
    }

    /// Catch typos in ids up front instead of in the middle of a playthrough.
    fn validate(&self) -> Result<(), String> {
        let room_exists = |id: &str| self.rooms.iter().any(|r| r.id == id);
        let mut problems = Vec::new();

        if !room_exists(&self.start.0) {
            problems.push(format!("start room `{}` does not exist", self.start.0));
        }
        if let Some(intro) = &self.intro
            && !self.nodes.contains_key(intro)
        {
            problems.push(format!("intro node `{intro}` does not exist"));
        }
        for room in &self.rooms {
            if let Some(enter) = &room.enter
                && !self.nodes.contains_key(enter)
            {
                problems.push(format!("room `{}`: enter node `{enter}` does not exist", room.id));
            }
            for h in &room.hotspots {
                if let Some((to, _)) = &h.exit
                    && !room_exists(to)
                {
                    problems.push(format!("exit `{}` leads to unknown room `{to}`", h.id));
                }
            }
        }
        for (name, lines) in &self.nodes {
            for line in lines {
                match &line.kind {
                    LineKind::Jump(t) | LineKind::Choice { target: t, .. }
                        if t != "end" && !self.nodes.contains_key(t) =>
                    {
                        problems.push(format!("node `{name}`: unknown node `{t}`"));
                    }
                    LineKind::Give(item) | LineKind::Remove(item) if self.item(item).is_none() => {
                        problems.push(format!("node `{name}`: unknown item `{item}`"));
                    }
                    LineKind::Goto(room, _) if !room_exists(room) => {
                        problems.push(format!("node `{name}`: unknown room `{room}`"));
                    }
                    _ => {}
                }
            }
        }
        if problems.is_empty() {
            Ok(())
        } else {
            problems.sort();
            Err(format!("story.txt has problems:\n  {}", problems.join("\n  ")))
        }
    }
}

fn parse_num(s: &str) -> Result<f32, String> {
    s.trim().parse().map_err(|_| format!("`{s}` is not a number"))
}

fn parse_color(s: &str) -> Result<[u8; 3], String> {
    let hex = s.strip_prefix('#').filter(|h| h.len() == 6).ok_or("colour must look like #rrggbb")?;
    let byte = |i: usize| u8::from_str_radix(&hex[i..i + 2], 16).map_err(|_| "bad hex colour".to_string());
    Ok([byte(0)?, byte(2)?, byte(4)?])
}

fn parse_conds(s: &str) -> Vec<Cond> {
    s.split_whitespace()
        .map(|c| match c.strip_prefix('!') {
            Some(flag) => Cond { flag: flag.to_string(), negate: true },
            None => Cond { flag: c.to_string(), negate: false },
        })
        .collect()
}

fn parse_room_line(room: &mut Room, line: &str) -> Result<(), String> {
    let (key, rest) = line.split_once(' ').ok_or("expected a room property")?;
    let rest = rest.trim();
    match key {
        "background:" => room.background = rest.to_string(),
        "enter:" => room.enter = Some(rest.to_string()),
        "music:" => room.music = Some(rest.to_string()),
        "sky:" => room.sky = Some(rest.to_string()),
        "light:" => room.light = parse_color(rest)?,
        "effect" => {
            let usage = "expected `effect <kind>: x y w h [| count N] [| if <conditions>]`";
            let (kind, rest) = rest.split_once(':').ok_or(usage)?;
            let kind = EffectKind::parse(kind.trim()).ok_or_else(|| {
                format!("unknown effect `{}` (try birds, sparkles, motes, leaves, smoke, sparks, glow)", kind.trim())
            })?;
            let mut fields = rest.split('|').map(str::trim);
            let nums: Vec<f32> = fields.next().unwrap_or_default().split_whitespace().map(parse_num).collect::<Result<_, _>>()?;
            let [x, y, w, h] = nums[..] else {
                return Err(usage.into());
            };
            let mut effect = Effect { kind, rect: Rect { x, y, w, h }, count: 1, conds: Vec::new() };
            for field in fields {
                let (opt, value) = field.split_once(' ').ok_or(usage)?;
                match opt {
                    "count" => effect.count = parse_num(value)? as u32,
                    "if" => effect.conds = parse_conds(value),
                    _ => return Err(format!("unknown effect option `{opt}`")),
                }
            }
            room.effects.push(effect);
        }
        "floor:" => {
            let (a, b) = rest.split_once(' ').ok_or("expected `floor: <top> <bottom>`")?;
            room.floor = (parse_num(a)?, parse_num(b)?);
        }
        "hotspot" | "exit" => {
            let (id, rest) = rest.split_once(':').ok_or("expected `hotspot id: Name | x y w h`")?;
            let mut fields = rest.split('|').map(str::trim);
            let name = fields.next().unwrap_or_default().to_string();
            let nums: Vec<f32> = fields
                .next()
                .ok_or("missing `x y w h`")?
                .split_whitespace()
                .map(parse_num)
                .collect::<Result<_, _>>()?;
            let [x, y, w, h] = nums[..] else {
                return Err("expected four numbers: x y w h".into());
            };
            let mut hotspot = Hotspot {
                id: id.trim().to_string(),
                name,
                rect: Rect { x, y, w, h },
                sprite: None,
                frames: None,
                conds: Vec::new(),
                exit: None,
            };
            for field in fields {
                let (opt, value) = field.split_once(' ').ok_or("expected `sprite`, `if` or `to`")?;
                match opt {
                    "sprite" => hotspot.sprite = Some(value.trim().to_string()),
                    "frames" => {
                        let (count, fps) = value.trim().split_once(' ').ok_or("expected `frames <count> <per second>`")?;
                        hotspot.frames = Some((parse_num(count)? as u32, parse_num(fps)?));
                    }
                    "if" => hotspot.conds = parse_conds(value),
                    "to" => {
                        let (to, x) = value.trim().split_once(' ').ok_or("expected `to <room> <x>`")?;
                        hotspot.exit = Some((to.to_string(), parse_num(x)?));
                    }
                    _ => return Err(format!("unknown hotspot option `{opt}`")),
                }
            }
            let numbered = hotspot.sprite.as_deref().is_some_and(|s| s.contains("{}"));
            if numbered != hotspot.frames.is_some() {
                return Err("an animated sprite needs both `{}` in its path and `| frames <count> <per second>`".into());
            }
            if key == "exit" && hotspot.exit.is_none() {
                return Err("exits need `| to <room> <x>`".into());
            }
            room.hotspots.push(hotspot);
        }
        _ => return Err(format!("unknown room property `{key}`")),
    }
    Ok(())
}

fn parse_node_line(line: &str) -> Result<Line, String> {
    let (conds, line) = match line.strip_prefix('[') {
        Some(rest) => {
            let (conds, rest) = rest.split_once(']').ok_or("missing `]`")?;
            (parse_conds(conds), rest.trim())
        }
        None => (Vec::new(), line),
    };
    let (word, rest) = line.split_once(' ').unwrap_or((line, ""));
    let rest = rest.trim().to_string();
    let kind = match word {
        "choice" => {
            let (choice_conds, text) = match rest.strip_prefix('[') {
                Some(r) => {
                    let (c, t) = r.split_once(']').ok_or("missing `]`")?;
                    (parse_conds(c), t.trim())
                }
                None => (Vec::new(), rest.as_str()),
            };
            let (text, target) = text.rsplit_once("->").ok_or("choices need `-> <node>`")?;
            let kind = LineKind::Choice { text: text.trim().to_string(), target: target.trim().to_string() };
            return Ok(Line { conds: conds.into_iter().chain(choice_conds).collect(), kind });
        }
        "jump" => LineKind::Jump(rest),
        "set" => LineKind::Set(rest),
        "clear" => LineKind::Clear(rest),
        "give" => LineKind::Give(rest),
        "remove" => LineKind::Remove(rest),
        "goto" => {
            let (room, x) = rest.split_once(' ').ok_or("expected `goto <room> <x>`")?;
            LineKind::Goto(room.to_string(), parse_num(x)?)
        }
        "end" => LineKind::End,
        "win" => LineKind::Win,
        _ => {
            let (speaker, text) = line.split_once(':').ok_or("expected `Speaker: text` or a command")?;
            LineKind::Say { speaker: speaker.trim().to_string(), text: text.trim().to_string() }
        }
    };
    Ok(Line { conds, kind })
}

/// Everything that changes during play.
#[derive(Clone, Debug, Default)]
pub struct GameState {
    pub room: String,
    pub flags: HashSet<String>,
    pub inventory: Vec<String>,
    pub won: bool,
}

impl GameState {
    /// A condition holds if the flag is set or the item is held (or neither, when negated).
    pub fn check(&self, conds: &[Cond]) -> bool {
        conds.iter().all(|c| {
            let set = self.flags.contains(&c.flag) || self.inventory.contains(&c.flag);
            set != c.negate
        })
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Choice {
    pub text: String,
    pub target: String,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Step {
    Say { speaker: String, text: String },
    Choices(Vec<Choice>),
    GotoRoom { room: String, x: f32 },
    Done,
}

/// Walks through a node's lines, applying commands, until something needs the player.
#[derive(Clone, Debug)]
pub struct Dialogue {
    node: String,
    line: usize,
    choices: Vec<Choice>,
    finished: bool,
}

impl Dialogue {
    pub fn new(node: impl Into<String>) -> Self {
        Dialogue { node: node.into(), line: 0, choices: Vec::new(), finished: false }
    }

    pub fn next(&mut self, story: &Story, state: &mut GameState) -> Step {
        loop {
            if self.finished {
                return Step::Done;
            }
            let lines = &story.nodes[&self.node];
            let Some(line) = lines.get(self.line) else {
                self.finished = true;
                return match std::mem::take(&mut self.choices) {
                    choices if choices.is_empty() => Step::Done,
                    choices => Step::Choices(choices),
                };
            };
            self.line += 1;
            if !state.check(&line.conds) {
                continue;
            }
            match &line.kind {
                LineKind::Say { speaker, text } => {
                    return Step::Say { speaker: speaker.clone(), text: text.clone() };
                }
                LineKind::Choice { text, target } => {
                    self.choices.push(Choice { text: text.clone(), target: target.clone() });
                }
                LineKind::Jump(node) => self.jump(node),
                LineKind::Set(flag) => {
                    state.flags.insert(flag.clone());
                }
                LineKind::Clear(flag) => {
                    state.flags.remove(flag);
                }
                LineKind::Give(item) => {
                    if !state.inventory.contains(item) {
                        state.inventory.push(item.clone());
                    }
                }
                LineKind::Remove(item) => state.inventory.retain(|i| i != item),
                LineKind::Goto(room, x) => {
                    state.room = room.clone();
                    return Step::GotoRoom { room: room.clone(), x: *x };
                }
                LineKind::End => self.finished = true,
                LineKind::Win => state.won = true,
            }
        }
    }

    pub fn choose(&mut self, target: &str) {
        if target == "end" {
            self.finished = true;
        } else {
            self.jump(target);
        }
    }

    fn jump(&mut self, node: &str) {
        self.node = node.to_string();
        self.line = 0;
        self.choices.clear();
        self.finished = false;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const STORY: &str = include_str!("../assets/story.txt");
    const SAUNA: &str = include_str!("../assets/sauna.txt");
    /// Every tale, for the checks that apply to them all.
    const STORIES: [(&str, &str); 2] = [("story.txt", STORY), ("sauna.txt", SAUNA)];

    fn new_game(story: &Story) -> GameState {
        GameState { room: story.start.0.clone(), ..Default::default() }
    }

    /// Run a node to the end, picking choices by their text. Returns everything said.
    fn play(story: &Story, state: &mut GameState, node: &str, mut picks: &[&str]) -> Vec<String> {
        let mut d = Dialogue::new(node);
        let mut said = Vec::new();
        loop {
            match d.next(story, state) {
                Step::Say { speaker, text } => said.push(format!("{speaker}: {text}")),
                Step::Choices(choices) => {
                    let (pick, rest) = picks.split_first().expect("ran out of choices to pick");
                    let choice = choices.iter().find(|c| c.text.starts_with(pick)).expect(pick);
                    d.choose(&choice.target);
                    picks = rest;
                }
                Step::GotoRoom { .. } => {}
                Step::Done => return said,
            }
        }
    }

    /// Apply a verb (or an item) to a hotspot the way the game does.
    fn interact(story: &Story, state: &mut GameState, verb: Verb, item: Option<&str>, target: &str) -> Vec<String> {
        let node = story.interaction_node(verb, item, target).expect("no node and no default");
        play(story, state, &node, &[])
    }

    #[test]
    fn story_file_parses_and_validates() {
        let story = Story::parse(STORY).unwrap();
        assert_eq!(story.rooms.len(), 3);
        assert!(story.nodes.contains_key("talk_kyllikki"));
    }

    #[test]
    fn every_story_parses_with_a_title_and_ending() {
        for (file, src) in STORIES {
            let story = Story::parse(src).unwrap_or_else(|e| panic!("{file}: {e}"));
            assert!(story.title.is_some() && story.ending.is_some(), "{file} needs a title and an ending");
        }
    }

    #[test]
    fn every_asset_the_story_uses_exists() {
        for (file, src) in STORIES {
            let story = Story::parse(src).unwrap();
            assets_exist(file, &story);
        }
    }

    fn assets_exist(file: &str, story: &Story) {
        let mut paths: Vec<String> = Vec::new();
        for room in &story.rooms {
            paths.push(room.background.clone());
            paths.extend(room.sky.clone());
            paths.extend(room.music.clone());
            paths.extend(room.hotspots.iter().flat_map(|h| h.sprite_frames()));
        }
        paths.extend(story.ending_music.clone());
        paths.extend(story.items.iter().map(|i| i.icon.clone()));
        for voice in story.characters.values().filter_map(|c| c.voice.as_ref()) {
            paths.extend((0..VOICE_SYLLABLES).map(|i| format!("{}/{i}.ogg", voice.dir)));
        }
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("assets");
        let missing: Vec<_> = paths.iter().filter(|p| !root.join(p).exists()).collect();
        assert!(missing.is_empty(), "{file}: missing assets: {missing:?}");
    }

    /// The game stretches each image to its room or hotspot size, so painted art must be
    /// exactly ART_SCALE times larger (characters may be painted at twice that, for detail),
    /// or it would be distorted.
    #[test]
    fn art_matches_room_and_hotspot_sizes() {
        const ART_SCALE: f32 = 4.0;
        fn png_size(path: &std::path::Path) -> (u32, u32) {
            let bytes = std::fs::read(path).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
            let be = |i: usize| u32::from_be_bytes(bytes[i..i + 4].try_into().unwrap());
            (be(16), be(20))
        }
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("assets");
        let mut wrong = Vec::new();
        let stories: Vec<Story> = STORIES.iter().map(|(_, src)| Story::parse(src).unwrap()).collect();
        for room in stories.iter().flat_map(|story| &story.rooms) {
            let expected = ((ROOM_WIDTH * ART_SCALE) as u32, (ROOM_HEIGHT * ART_SCALE) as u32);
            let actual = png_size(&root.join(&room.background));
            if actual != expected {
                wrong.push(format!("{}: {actual:?}, expected {expected:?}", room.background));
            }
            if let Some(sky) = &room.sky {
                let expected = (expected.0 * 2, expected.1); // twice as wide, to drift across
                let actual = png_size(&root.join(sky));
                if actual != expected {
                    wrong.push(format!("{sky}: {actual:?}, expected {expected:?}"));
                }
            }
            for h in &room.hotspots {
                let at = |k: f32| ((h.rect.w * ART_SCALE * k) as u32, (h.rect.h * ART_SCALE * k) as u32);
                let (expected, detailed) = (at(1.0), at(2.0));
                for sprite in h.sprite_frames() {
                    let actual = png_size(&root.join(&sprite));
                    if actual != expected && actual != detailed {
                        wrong.push(format!("{sprite} (hotspot {}): {actual:?}, expected {expected:?}", h.id));
                    }
                }
            }
        }
        assert!(wrong.is_empty(), "art at the wrong size:\n  {}", wrong.join("\n  "));
    }

    #[test]
    fn effects_parse_with_counts_and_conditions() {
        let src = "start: a 10\nroom a: A\n  effect sparkles: 1 2 3 4 | count 12\n  effect smoke: 5 6 7 8 | if fire_lit\n";
        let story = Story::parse(src).unwrap();
        let effects = &story.room("a").effects;
        assert_eq!((effects[0].kind, effects[0].count), (EffectKind::Sparkles, 12));
        assert_eq!(effects[1].conds, parse_conds("fire_lit"));
        let err = Story::parse("start: a 10\nroom a: A\n  effect fireworks: 1 2 3 4\n").unwrap_err();
        assert!(err.contains("unknown effect `fireworks`"), "{err}");
    }

    #[test]
    fn animated_sprites_need_frames_and_a_numbered_path() {
        let ok = "start: a 10\nroom a: A\n  hotspot f: F | 1 2 3 4 | sprite fire_{}.png | frames 3 10\n";
        let story = Story::parse(ok).unwrap();
        assert_eq!(story.room("a").hotspots[0].sprite_frames(), ["fire_0.png", "fire_1.png", "fire_2.png"]);
        let missing = Story::parse("start: a 10\nroom a: A\n  hotspot f: F | 1 2 3 4 | sprite fire_{}.png\n");
        assert!(missing.unwrap_err().contains("animated sprite"));
    }

    #[test]
    fn validation_catches_typos() {
        let src = "start: a 10\nroom a: A\n  exit e: E | 0 0 1 1 | to nowhere 5\nnode n\n  jump missing\n  give ghost\n";
        let err = Story::parse(src).unwrap_err();
        assert!(err.contains("unknown room `nowhere`"), "{err}");
        assert!(err.contains("unknown node `missing`"), "{err}");
        assert!(err.contains("unknown item `ghost`"), "{err}");
    }

    #[test]
    fn parse_errors_point_at_the_line() {
        let err = Story::parse("start: a 10\nroom a: A\n  hotspot h: H | 1 2 3\n").unwrap_err();
        assert!(err.contains("line 3"), "{err}");
    }

    #[test]
    fn conditions_check_flags_and_items() {
        let mut s = GameState::default();
        let cond = parse_conds("bread !fire_lit");
        assert!(!s.check(&cond));
        s.inventory.push("bread".into());
        assert!(s.check(&cond));
        s.flags.insert("fire_lit".into());
        assert!(!s.check(&cond));
    }

    #[test]
    fn interactions_fall_back_to_defaults() {
        let story = Story::parse(STORY).unwrap();
        assert_eq!(story.interaction_node(Verb::Look, None, "hearth").unwrap(), "look_hearth");
        assert_eq!(story.interaction_node(Verb::Talk, None, "hearth").unwrap(), "default_talk");
        assert_eq!(story.interaction_node(Verb::Use, Some("bread"), "stone").unwrap(), "use_bread_stone");
        assert_eq!(story.interaction_node(Verb::Use, Some("bread"), "hearth").unwrap(), "default_use_item");
    }

    #[test]
    fn hidden_hotspots_cannot_be_clicked() {
        let story = Story::parse(STORY).unwrap();
        let mut state = new_game(&story);
        let village = story.room("village");
        assert_eq!(village.hotspot_at(55.0, 100.0, &state).unwrap().id, "bread");
        state.flags.insert("took_bread".into());
        // Now the stump underneath is what you click.
        assert_eq!(village.hotspot_at(55.0, 103.0, &state).unwrap().id, "stump");
    }

    #[test]
    fn player_stands_beside_hotspots() {
        let story = Story::parse(STORY).unwrap();
        let village = story.room("village");
        let kyllikki = village.hotspots.iter().find(|h| h.id == "kyllikki").unwrap();
        let (from_left, _) = village.walk_point(kyllikki, 100.0);
        let (from_right, _) = village.walk_point(kyllikki, 300.0);
        assert!(from_left < kyllikki.rect.x);
        assert!(from_right > kyllikki.rect.x + kyllikki.rect.w);
    }

    #[test]
    fn grove_refuses_tinder_until_offered() {
        let story = Story::parse(STORY).unwrap();
        let mut state = new_game(&story);
        interact(&story, &mut state, Verb::Take, None, "tinder");
        assert!(!state.inventory.contains(&"tinder".to_string()));
    }

    #[test]
    fn full_walkthrough_wins_the_game() {
        let story = Story::parse(STORY).unwrap();
        let mut s = new_game(&story);
        let intro = story.intro.clone().unwrap();
        play(&story, &mut s, &intro, &[]);

        play(&story, &mut s, "talk_kyllikki", &["Do you know the origin", "Goodbye"]);
        interact(&story, &mut s, Verb::Take, None, "bread");
        interact(&story, &mut s, Verb::Take, None, "button");
        // Too early: no words yet.
        interact(&story, &mut s, Verb::Use, Some("button"), "hearth");
        assert!(!s.won);

        interact(&story, &mut s, Verb::Use, Some("button"), "magpie");
        assert!(s.inventory.contains(&"spindle".to_string()));
        interact(&story, &mut s, Verb::Use, Some("spindle"), "kyllikki");
        assert!(s.flags.contains("knows_fire"));

        interact(&story, &mut s, Verb::Use, Some("bread"), "stone");
        interact(&story, &mut s, Verb::Take, None, "tinder");
        assert!(s.inventory.contains(&"tinder".to_string()));

        let said = interact(&story, &mut s, Verb::Use, Some("tinder"), "hearth");
        assert!(said.iter().any(|l| l.contains("tietäjä yet")));
        assert!(s.won);
        assert!(s.inventory.is_empty());
    }

    #[test]
    fn sauna_walkthrough_wins_the_game() {
        let story = Story::parse(SAUNA).unwrap();
        let mut s = new_game(&story);
        let intro = story.intro.clone().unwrap();
        play(&story, &mut s, &intro, &[]);

        // The steam bites; Kyllikki explains what the keeper wants.
        interact(&story, &mut s, Verb::Use, None, "kiuas");
        assert!(s.flags.contains("felt_bite"));
        play(&story, &mut s, "talk_kyllikki", &["The steam in there bites", "Goodbye"]);
        assert!(s.flags.contains("knows_amends"));

        // Who offended it: the feather, the magpie, and Kyllikki's confession.
        interact(&story, &mut s, Verb::Take, None, "feather");
        interact(&story, &mut s, Verb::Use, Some("feather"), "kyllikki");
        assert!(!s.flags.contains("knows_culprit"), "not before hearing the magpie");
        interact(&story, &mut s, Verb::Talk, None, "magpie");
        interact(&story, &mut s, Verb::Use, Some("feather"), "kyllikki");
        assert!(s.flags.contains("knows_culprit"));
        play(&story, &mut s, "talk_kyllikki", &["Will you apologise", "Goodbye"]);
        assert!(!s.flags.contains("kyllikki_in_sauna"), "not until the sauna is ready");

        // Clean water.
        interact(&story, &mut s, Verb::Take, None, "bucket");
        interact(&story, &mut s, Verb::Use, Some("bucket"), "lake");
        assert!(s.inventory.contains(&"water".to_string()));

        // A vihta: silver for the grove, twigs from the birch, bound by Kyllikki.
        interact(&story, &mut s, Verb::Take, None, "birch");
        assert!(!s.inventory.contains(&"twigs".to_string()), "the grove gives nothing for free");
        interact(&story, &mut s, Verb::Take, None, "coin");
        interact(&story, &mut s, Verb::Use, Some("coin"), "stone");
        interact(&story, &mut s, Verb::Take, None, "birch");
        interact(&story, &mut s, Verb::Use, Some("twigs"), "kyllikki");
        assert!(s.inventory.contains(&"vihta".to_string()));

        // Grandfather's words, once the smoke clears.
        interact(&story, &mut s, Verb::Look, None, "beam");
        assert!(!s.flags.contains("knows_loyly"));
        interact(&story, &mut s, Verb::Use, None, "vent");
        interact(&story, &mut s, Verb::Look, None, "beam");
        assert!(s.flags.contains("knows_loyly"));

        // The vihta can't be left, nor the water thrown, before the apology.
        interact(&story, &mut s, Verb::Use, Some("vihta"), "benches");
        assert!(!s.flags.contains("vihta_left"));
        interact(&story, &mut s, Verb::Use, Some("water"), "kiuas");
        assert!(!s.won);

        // Kyllikki comes to the sauna, and has to say it properly.
        play(&story, &mut s, "talk_kyllikki", &["The sauna's ready"]);
        assert!(s.flags.contains("kyllikki_in_sauna"));
        let said = play(&story, &mut s, "talk_kyllikki", &["Just tell it", "Tell it the magpie", "Ask its forgiveness"]);
        assert!(said.iter().filter(|l| l.starts_with("Keeper: H")).count() == 2, "{said:?}");
        assert!(s.flags.contains("apologized"));

        interact(&story, &mut s, Verb::Use, Some("vihta"), "benches");
        let said = interact(&story, &mut s, Verb::Use, Some("water"), "kiuas");
        assert!(said.iter().any(|l| l.contains("Grandfather?")));
        assert!(s.won);
    }
}

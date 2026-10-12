+++
id = "forces"
title = "Forces and Newton's Laws"
+++
# Physics Source Material for ${name} — Unit 1: Forces and Newton's Laws

> Teaching notes for Claude. Rewritten from scratch for clarity: short, plain wording, new worked examples, answers included.
> Standard introductory physics; lesson order follows OpenStax *Physics* ch. 4 (4.1 Force, 4.2 First Law, 4.3 Second Law, 4.4 Third Law).
> No passages, figures or textbook examples are copied. Reading level for ${name}: ${reading_level}, math in small explained steps. ${He} is precocious.

## Sources (credit; verify licenses before sharing outside the family)

| Source | Role | License as seen 2026-10-10 |
| --- | --- | --- |
| OpenStax, *Physics* (Urone and Hinrichs, 2020), ch. 4. https://openstax.org/books/physics/pages/preface | Order and ideas of the lessons | CC BY 4.0 per preface; page also showed a "noncommercial" note and a CC BY-NC-SA footer. Verify. |
| PhET *Forces and Motion: Basics*. https://phet.colorado.edu/en/simulations/forces-and-motion-basics | The interactive activity (link only) | Metadata linked CC BY-NC 4.0 and GPL 2.0. Verify. |
| CK-12 Physics FlexBooks | Candidate for later units; not used | CC BY-NC 3.0 per Wikipedia. |

## Course map

Unit 1 (this file): acceleration warm-up → force → Newton's 1st, 2nd, 3rd laws.
Next, in this order: motion and acceleration → projectiles → gravity → momentum → energy → waves → circuits.

## The loop every lesson follows

**Hook** (a question) → **Idea** (2-3 sentences) → **Predict** (${name} guesses first) → **Work it** (one example, together) →
**Check** (one question) → **Try it** (do or simulate something) → **Link** (to Roblox or sports).
One idea per message. Ask, then wait.

---

## Lesson 0 — Acceleration (3-minute warm-up)

**Goal:** ${name} can say that acceleration means velocity is changing, in any direction.

- **Hook:** "At the very top of a jump in Roblox, your character stops for an instant. Is anything still changing?"
- **Idea:** *Speed* is how fast. *Velocity* is speed plus direction. *Acceleration* is how quickly velocity changes: speeding up, slowing down, or turning.
- **Work it:** A scooter goes from 0 to 6 m/s in 3 seconds. It gains 6 m/s over 3 s, so a = 6 ÷ 3 = **2 m/s²** (it gains 2 m/s every second).
  Now a skater slows from 8 m/s to 2 m/s in 3 s. The change is −6 m/s over 3 s, so a = **−2 m/s²**. Slowing down counts too.
- **Predict:** "A car circles a roundabout at a steady 20 km/h. Is it accelerating?"
- **Check answers:**
  - Roundabout: **Yes.** Its direction keeps changing, so its velocity changes.
  - Ball thrown straight up, top of its flight: **No, acceleration isn't zero.** Velocity is zero for an instant, but gravity keeps changing it by about 10 m/s every second.
- **Draw it:** (a checked text diagram; use it as written, or redraw it with the child's own numbers)
  ```
  Each dot is one second; the arrow is the velocity.

  speeding up:   o->   o-->   o---->   o------>
  slowing down:  o------>   o---->   o-->   o->
  turning:       same length, but a new direction each time
  ```
- **Try it:** Walk across the room, speeding up each second as you count. Then walk steadily. Which was acceleration?
- **Link:** A Roblox jump rises, slows, pauses, and falls. Gravity is accelerating the character the whole time.
- **Think about:** Next time you ride in a car or bus, notice what your body feels when it speeds up, slows down and turns. Which of those is acceleration?
- **Picture:** velocity_change  (offer only if the text diagram is not enough; see SKILL.md)
- **Watch for:** "Acceleration means fast." "Nothing happens at the top." Both confuse velocity with how it changes.

## Lesson 1 — Force

**Goal:** ${name} can name forces on an object, say what a *vector* is, and combine forces into a net force.

- **Hook:** "Two kids pull on a rope. When does the rope move?"
- **Idea:** A *force* is a push or a pull. It has a size and a direction. We measure it in **newtons (N)**; 1 N is about the weight of a small apple.
  Anything with both a size and a direction is called a **vector**: force, velocity and acceleration are vectors. A number with a size only, like mass or time, is not.
  The *net force* is all the forces on an object added up, with opposite directions subtracting.
- **Work it:** Tug of war: 30 N pulls left, 20 N pulls right. Net = 30 − 20 = **10 N to the left**. The rope slides left.
  Shopping cart: you push 15 N forward, the floor's friction pushes 5 N back. Net = **10 N forward**.
  Balanced case: 25 N each way, net = **0**, so the rope doesn't speed up or slow down.
- **Free-body diagram (the "arrow picture"):** draw the object as a dot, then one arrow per force, longer arrow = stronger force.
- **Predict:** "A book rests on a table. Are there any forces on it?" (Yes: gravity pulls down, the table pushes up, and they balance.)
- **Check:** "Is 5 kilograms a vector? Is 5 newtons pointing north?" (No: mass has no direction. Yes.) Then: "Three friends push a box: 10 N east, 10 N east, 15 N west. What is the net force?" (**5 N east.**)
- **Draw it:** (a checked text diagram; use it as written, or redraw it with the child's own numbers)
  ```
       30 N                20 N
  <=============== [rope] ==========>
  net force = 30 - 20 = 10 N, to the left
  ```
- **Try it:** PhET *Forces and Motion: Basics*: add pushers to each side, watch the arrows and the net force. Goal: tell balanced from unbalanced.
- **Link:** Conveyor belts and jump pads in Roblox are forces added to your character.
- **Think about:** Look around the room and find three things being pushed or pulled right now. What is doing the pushing or pulling?
- **Picture:** tug_of_war  (offer only if the text diagram is not enough; see SKILL.md)
- **Watch for:** Calling every quantity a vector, or treating the word as a label to memorise. Ask "does it have a direction?" "A force is something an object contains." A force is something one object does *to* another.

## Lesson 2 — Newton's First Law (inertia)

**Goal:** ${name} can explain that objects change their motion only when a net force acts.

- **Hook:** "You slide a coin across a table and it stops. Why? What if the table were perfectly slippery?"
- **Idea:** An object keeps doing what it's doing, still or moving straight at a steady speed, until a net force changes that. That stubbornness is *inertia*.
  *Mass* measures inertia: more mass, harder to start, stop or turn. *Friction* is a force that opposes sliding.
- **Work it:** A soccer ball rolls on grass and stops after 15 m, but on ice it travels much farther. Same ball, same push; only friction changed.
  Bowling ball vs beach ball: the same kick changes the beach ball's motion far more, because it has less mass.
- **Predict:** "A puck slides in outer space with nothing touching it. What does it do?" (Keeps going in a straight line, forever.)
- **Check:** "A bus brakes suddenly. Why do you lurch forward?" (Your body keeps moving; the seat and belt are what slow you down.)
- **Draw it:** (a checked text diagram; use it as written, or redraw it with the child's own numbers)
  ```
  grass (friction):  o---->  o--->  o-->  o>  stops
  ice (little):      o---->  o---->  o--->  o--->  coasts on
  space (none):      o---->  o---->  o---->  o---->  forever
  ```
- **Try it:** Slide a coin on a table, then on a towel. Then PhET: change the friction and compare how far the crate coasts.
- **Link:** A Roblox character slides on an ice part because there is little friction.
- **Think about:** Think of a ball rolling across grass, then across ice. Why does it stop sooner on grass? What is pushing against it?
- **Picture:** balanced_book  (offer only if the text diagram is not enough; see SKILL.md)
- **Watch for:** "Things naturally stop." They stop because forces, such as friction, act on them.

## Lesson 3 — Newton's Second Law (F = m × a)

**Goal:** ${name} can predict acceleration from force and mass, and compute one from the other two.

- **Hook:** "You and a friend push a shopping cart: one empty, one full. Which one speeds up faster with the same push?"
- **Idea:** Net force makes things accelerate. Bigger force, bigger acceleration; more mass, smaller acceleration. **F = m × a**, with F in newtons, m in kilograms, a in m/s².
  One newton is the push that speeds up a 1 kg object by 1 m/s every second.
- **Work it:**
  - Find acceleration: a net push of 12 N on a 4 kg wagon gives a = 12 ÷ 4 = **3 m/s²**. The same push on a 6 kg wagon gives 12 ÷ 6 = **2 m/s²**.
  - Find force: a 30 kg sled speeds up at 2 m/s². Net force = 30 × 2 = **60 N**.
  - Weight is a force: **W = m × g**, with g ≈ 9.8 m/s². A 5 kg backpack weighs about 5 × 9.8 ≈ **49 N**. On the Moon it has the same mass but weighs about one-sixth as much (about 8 N).
- **Predict:** "If we double the push on the same wagon, what happens to the acceleration? If we double the mass instead?"
- **Check:** "A 5 kg cart accelerates at 4 m/s². What net force acts on it?" (**20 N**)
- **Draw it:** (a checked text diagram; use it as written, or redraw it with the child's own numbers)
  ```
  same 12 N push, different mass:

  12 N ==> [ 4 kg ]    a = 12 / 4 = 3 m/s²  (speeds up more)
  12 N ==> [ 6 kg ]    a = 12 / 6 = 2 m/s²
  ```
- **Try it:** Stand on a bathroom scale and press down on a table. The reading changes. Which force did the scale feel?
- **Link:** In Roblox, a heavy part and a light part given the same push move differently. Later, a short Lua script can test this (see the Roblox Lua lesson plan in the kids folder).
- **Think about:** Picture pushing an empty shopping cart, then a full one with the same push. Which speeds up more, and why do you think so?
- **Picture:** same_push  (offer only if the text diagram is not enough; see SKILL.md)
- **Watch for:** "Mass and weight are the same." Mass is how much stuff; weight is gravity's pull on it.

## Lesson 4 — Newton's Third Law (pairs)

**Goal:** ${name} can name the pair of forces in an interaction and say why they don't cancel.

- **Hook:** "You push a wall as hard as you can. Does the wall do anything to you?"
- **Idea:** Forces come in **pairs** between two objects: when A pushes B, B pushes A back just as hard, in the opposite direction.
  The pair acts on **different** objects, so the two forces never cancel each other.
- **Work it:** Two skaters on smooth ice push off each other with 120 N. Skater A has mass 40 kg and skater B has 60 kg.
  The forces are equal and opposite, but accelerations differ (second law): A gets 120 ÷ 40 = **3 m/s²**, B gets 120 ÷ 60 = **2 m/s²**, in opposite directions.
- **Everyday pairs:** walking (your foot pushes the ground back, the ground pushes you forward); swimming off a wall; a rocket pushing exhaust out while the exhaust pushes the rocket.
- **Predict:** "You're floating in space and throw a heavy ball away. What happens to you?" (You drift the other way.)
- **Check:** "Does a rocket need air to push against?" (**No.** The pair is rocket and exhaust, so rockets work in empty space.)
- **Draw it:** (a checked text diagram; use it as written, or redraw it with the child's own numbers)
  ```
  push on A: 120 N              push on B: 120 N
  <============= [ A ] [ B ] =============>
  A: 40 kg, a = 3 m/s² left     B: 60 kg, a = 2 m/s² right
  ```
- **Try it:** Sit on a rolling chair and push off a wall. Or hang an eraser on a rubber band and watch the band stretch.
- **Link:** Knockback and recoil in games are third-law pairs.
- **Think about:** When you kick a soccer ball, the ball pushes back on your foot. Can you remember feeling that? Would a heavier ball push back harder?
- **Picture:** skaters  (offer only if the text diagram is not enough; see SKILL.md)
- **Watch for:** "Equal and opposite forces cancel, so nothing can move." They act on different objects.

---

## Unit wrap-up

Ask ${name} to say each law in his own words: **1** stays the same unless pushed, **2** more push = more change, more mass = less change, **3** pushes come in pairs.
Challenge: "Design a Roblox jump no character could ever make, and tell me which law it breaks."

## Quiz bank (one at a time; hold the answer until ${name} tries)

1. A hockey puck slides on ice and slowly stops. Which force stops it? (**Friction**)
2. A 3 kg box gets a net push of 12 N. What is its acceleration? (**4 m/s²**)
3. Which has more inertia, a bowling ball or a beach ball? How could you tell by pushing? (**Bowling ball**; it's harder to start or stop.)
4. A box has 20 N pushing left and 20 N pushing right. Is it accelerating? (**No**; the net force is zero.)
5. You push a friend on a skateboard. Does the friend push back on you? How hard? (**Yes, equally hard**; that is why you may roll back too.)

---
name: no-trigger-react-button
description: skill must not load
tags: [trigger, negative]
runs: 3
max_turns: 4
allowed_tools: [Read, Glob, Grep, Skill]
---

This React button re-renders on every keystroke in a sibling input. How do I stop that?

```jsx
function Save({ onSave }) { return <button onClick={() => onSave()}>Save</button>; }
```

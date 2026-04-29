import { useReducer } from "react";

import type { DigitalHumanState } from "../components/DigitalHumanMock";

type DigitalHumanSnapshot = {
  state: DigitalHumanState;
  caption: string;
};

type DigitalHumanAction =
  | { type: "set"; state: DigitalHumanState; caption?: string }
  | { type: "caption"; caption: string }
  | { type: "reset"; caption?: string };

const DEFAULT_CAPTION = "你好，我是灵境。文本提问优先，语音会作为辅助输入。";

function reducer(current: DigitalHumanSnapshot, action: DigitalHumanAction): DigitalHumanSnapshot {
  if (action.type === "caption") {
    return { ...current, caption: action.caption };
  }
  if (action.type === "reset") {
    return { state: "welcome", caption: action.caption || DEFAULT_CAPTION };
  }
  return {
    state: action.state,
    caption: action.caption || current.caption,
  };
}

export function useDigitalHumanState(initialCaption = DEFAULT_CAPTION) {
  const [snapshot, dispatch] = useReducer(reducer, {
    state: "welcome" as DigitalHumanState,
    caption: initialCaption,
  });

  return {
    ...snapshot,
    resetHuman: (caption?: string) => dispatch({ type: "reset", caption }),
    setHumanCaption: (caption: string) => dispatch({ type: "caption", caption }),
    setHumanState: (state: DigitalHumanState, caption?: string) => dispatch({ type: "set", state, caption }),
  };
}

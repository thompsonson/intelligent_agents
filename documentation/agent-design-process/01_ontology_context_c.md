Verified and working. Here's the final version:

```hy
;; A minimal LLM agent loop: percept -> action, persistent context only.
;; No tools, no DSA, no PDDL predicates -- just STOP-CHECK + re-arm LLM.QUERY,
;; the two real moving parts of agent-function.md's abstract loop.
;;
;;   function AGENT-FUNCTION(percept) returns an action
;;       persistent: context          ; the conversation so far
;;
;;       if percept is a prompt:
;;           context <- context + [user: percept]
;;           return LLM.QUERY(context)
;;
;;       elif percept is a model response:
;;           context <- context + [assistant: response]
;;           if STOP-CHECK(response):
;;               return REPORT(response)
;;           else:
;;               return LLM.QUERY(context)

(setv context [])
(setv turns 0)

;; --- stand-in for a real LLM call. Swap for an openai/anthropic client;
;; the loop around it is unchanged either way. ---
(defn llm-query [ctx]
  (global turns)
  (setv turns (+ turns 1))
  (if (= turns 1)
      "Let me think about this further."
      "FINAL: 4"))

(defn stop-check [response]
  (.startswith response "FINAL:"))

(defn agent-function [percept]
  (setv kind    (get percept 0)
        content (get percept 1))
  (cond
    (= kind "prompt")
      (do (.append context {"role" "user" "content" content})
          ["LLM.QUERY" context])

    (= kind "response")
      (do (.append context {"role" "assistant" "content" content})
          (if (stop-check content)
              ["REPORT" content]
              ["LLM.QUERY" context]))))

;; --- the driver: "while not STOPPED", reduced to nothing but LLM.QUERY.
;; This is agent-loop-function.md's while-loop with everything except
;; STOP-CHECK and re-arm stripped out. ---
(defn run [prompt]
  (setv percept ["prompt" prompt])
  (while True
    (setv result (agent-function percept))
    (setv action (get result 0)
          arg    (get result 1))
    (cond
      (= action "LLM.QUERY")
        (do
          (setv response (llm-query arg))
          (print f"  LLM.QUERY -> {(repr response)}")
          (setv percept ["response" response]))
      (= action "REPORT")
        (do
          (print f"REPORT: {arg}")
          (break)))))

(run "What is 2 + 2?")
(print)
(print "Final context:")
(for [msg context]
  (setv role (get msg "role")
        content (get msg "content"))
  (print f"  {role}: {content}"))
```

Output:

```
  LLM.QUERY -> 'Let me think about this further.'
  LLM.QUERY -> 'FINAL: 4'
REPORT: FINAL: 4

Final context:
  user: What is 2 + 2?
  assistant: Let me think about this further.
  assistant: FINAL: 4
```

**What's kept vs. stripped, relative to `agent-function.md`:** this keeps only `context` (the minimum a multi-turn loop needs to exist at all — hard to call it "no context management" if there's literally no conversation), `STOP-CHECK` (final-answer vs. keep-going), and the re-arm of `LLM.QUERY`. Everything else — `belief`, `declared`, `pending`, `TOOLS.RESOLVE`/`VALIDATE`, `SAFETY.CHECK`, `DSA.INVOKE`, `PERMISSION.ASK` — is gone. The driver's `while True` + `cond` is `agent-loop-function.md`'s while-loop with every concern except the two above deleted.

`llm-query` is a stub (turn-counted canned responses) so this runs with zero credentials or network. Swap its body for a real client call (`openai`, `anthropic`) and nothing else changes — that's the point of the shape: the loop doesn't care what's behind `LLM.QUERY`.

Two Hy rough edges worth flagging since you'll hit them again: f-strings don't support Python's `!r`/`!s` conversion syntax (use `(repr x)` explicitly), and nested double-quotes inside an f-string's `{}` break the reader (pull the lookup out to a `setv` first, as I did for `role`/`content`).

Next natural step, if useful: add one tool call (say a single `read` action) so you can see `TOOLS.RESOLVE` → `DSA.INVOKE` → `BELIEF.MERGE` show up as one more branch in `agent-function`, before jumping all the way to the full PDDL-predicate version.
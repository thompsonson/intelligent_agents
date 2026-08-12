;; minimal_llm_loop.hy — the Step 5 toy loop against a real OpenAI-compatible server.
;;
;; Reads LLM_BASE_URL / LLM_MODEL / LLM_API_KEY / LLM_TEMPERATURE from the
;; environment (the repo's .env); defaults point at the computer server so the
;; script runs as-is. The agent-function and driver are unchanged from the
;; blog post's Step 5 — only the stub body of llm-query is swapped for a real
;; client call, exactly as the post's "swap the stub" note promises.
;;
;;   run with: source .env && .venv/bin/hy examples/minimal_llm_loop.hy [prompt]

(import os)
(import sys)
(import openai)

;; the only persistent state — context, Kind: controllable
(setv context [])

;; --- the real LLM.QUERY: OpenAI-compatible call to LLM_BASE_URL. ---
(defn llm-query [ctx]
  (setv client (openai.OpenAI
                 :base_url (os.getenv "LLM_BASE_URL" "http://computer:13305/api/v1")
                 :api_key  (os.getenv "LLM_API_KEY" "sk-test")))
  (setv resp (.create client.chat.completions
                      :model (os.getenv "LLM_MODEL" "Qwen3-Coder-30B-A3B-Instruct-GGUF")
                      :messages ctx
                      :temperature (float (os.getenv "LLM_TEMPERATURE" "0.7"))))
  (setv choice (get (. resp choices) 0))
  (. choice message content))

;; the derived predicates: is_final(response), answer(response)
(defn is-final [response]
  (.startswith response "FINAL:"))

(defn answer-of [response]
  (.strip (cut response (len "FINAL:") None)))

(defn agent-function [percept]
  (setv kind    (get percept 0)
        content (get percept 1))
  (cond
    (= kind "prompt")
      (do (.append context {"role" "user" "content" content})
          ["LLM.QUERY" context])
    (= kind "response")
      (do (.append context {"role" "assistant" "content" content})
          (if (is-final content)
              ["REPORT" (answer-of content)]
              ["LLM.QUERY" context]))))

;; the driver: dispatch on the returned action
(defn run [prompt]
  ;; seed the FINAL: format the stop-check depends on
  (.append context {"role" "system"
                    "content" "Answer the user's question. Prefix your final answer with FINAL:."})
  (setv percept ["prompt" prompt])
  (while True
    (setv result (agent-function percept))
    (setv action (get result 0)
          arg    (get result 1))
    (cond
      (= action "LLM.QUERY")
        (do (setv response (llm-query arg))
            (print f"  LLM.QUERY -> {response}")
            (setv percept ["response" response]))
      (= action "REPORT")
        (do (print f"REPORT: {arg}")
            (break)))))

(when (= __name__ "__main__")
  (run (if (>= (len sys.argv) 2)
           (get sys.argv 1)
           "What is 2 + 2?")))

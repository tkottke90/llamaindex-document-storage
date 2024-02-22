import { ChatMessage, MarkdownNodeParser, Ollama, serviceContextFromDefaults } from "llamaindex";
import { OLLAMA_BASE_URL, TIMEOUT_MIN } from "./config.js";
import { createWriteStream } from 'fs';

// Timeout is in MS so we need to make that configurable
const TIMEOUT_SEC = TIMEOUT_MIN * 60;

console.debug(`> [${new Date().toISOString()}] Timeout: ${Math.round(TIMEOUT_SEC)} secs`)

export const ollamaLLM = new Ollama({ model: "llama2", temperature: 1, baseURL: OLLAMA_BASE_URL, requestTimeout: TIMEOUT_SEC * 1000 });

export const serviceContext = serviceContextFromDefaults({
  llm: ollamaLLM,
  embedModel: ollamaLLM,
  nodeParser: new MarkdownNodeParser()
});

export function chat(...prompt: ChatMessage[]) {  
  return ollamaLLM.chat({ messages: prompt})
}

export function chatStream(prompt: string) {
  const stream = createWriteStream('./temp');
  
  stream.on('open', async (id) => {
    const response = await ollamaLLM.complete({ prompt, stream: true });

    for await(const chunk of response) {
      stream.write(chunk, 'utf-8');
    }

    stream.end();
  });

  return stream;
}
import { config } from 'dotenv';
config();

export const TIMEOUT_MIN = Number(process.env.TIMEOUT_MIN ?? 30);
export const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL ?? "http://127.0.0.1:11434";
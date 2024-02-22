import { readFileSync, existsSync, writeFileSync } from 'fs';
import path from 'path';
import "./config.js";
import { chat, serviceContext } from "./llm.js";
import { timer } from "./utils/timing.js";
import { ChatMessage, Document, MarkdownNodeParser, VectorStoreIndex, storageContextFromDefaults } from "llamaindex";
import { preprocessClassPrompt } from './prompts/class-pre-process.js';
import { RAG_LLM } from './prompts/rag-document.js';

const storageContext = await storageContextFromDefaults({
  persistDir: "./index-store",
});

async function main2() {
  console.log(`> [${new Date().toISOString()}] Loading Document`);

  const essay = readFileSync("docs/Fighter_Class.md", "utf-8");

  // Create Document object with essay
  const document = new Document({ text: essay });

  console.log(`> [${new Date().toISOString()}] Document Loaded`);

  console.log(`> [${new Date().toISOString()}] Creating Vectors`);
  // Split text and create embeddings. Store them in a VectorStoreIndex
  const index = await VectorStoreIndex.fromDocuments([document], { serviceContext, storageContext });

  console.log(`> [${new Date().toISOString()}] Vector Created`);

  // Query the index
  console.log(`> [${new Date().toISOString()}] Querying LLM`);
  const queryEngine = index.asQueryEngine();
  const t = timer();
  try {
    const response = await queryEngine.query({
      query: "What features does a fighter get at level 5?"
    });



    const response2 = await queryEngine.query({
      query: `You are an AI Assistant who is an expert in the Dungeons and Dragons 5e rule set.  Below is a question related to character leveling

CONTEXT:
${response.response}

CHARACTER INFO:
Bron is a level 4 battle master fighter, what improvements does he see at level 5?`
    });


    const r = t();

    // console.log();
    // for await (const chunk of response) {
    //   process.stdout.write(chunk.response);
    // }

    console.log(`> [${new Date().toISOString()}] Success Duration: ${r.sec} sec [${r.ms} ms]`);

    console.log(`> [${new Date().toISOString()}] Query Complete`);

    debugger;
    // Output response
    console.log(`
================
>   Response   <
================

${response2.response}
`);
  } catch (err) {
    const r = t();

    console.log(`> [${new Date().toISOString()}] Failed Duration: ${r.sec} sec [${r.ms} ms]`);

    throw err;
  }

  process.exit();
}

let db: { messages: ChatMessage[] } & Record<string, any> = { messages: [] };

if (existsSync('local-json-db.json')) {
  const data = readFileSync('local-json-db.json', 'utf-8');

  db = JSON.parse(data);
}

function saveDB() {
  writeFileSync('local-json-db.json', JSON.stringify(db, null, 2), 'utf-8');
}

async function main(prompt: string) {
  const t = timer();
  const system: ChatMessage = { role: 'system', content: `You are an AI Assistant specializing in processing documents and creating logical chunks.  Take the following document input and output a revised format which optimizes the document for storage in a Vector Database. Your response should simply be the updated organization of the file itself.  DO NOT ADD ANY CONVERSATIONAL TEXT to the output!` };
  const message: ChatMessage = { role: 'user', content: `INPUT: ${prompt}` };

  db.messages.push(system, message);

  const response = await chat(system, message);

  const r = t();
  console.log(`> [${new Date().toISOString()}] Success Duration: ${r.sec} sec [${r.ms} ms]`);

  db.messages.push(response.message);
}


const [ /* node */, /* file */, cmd, message ] = process.argv;

if (cmd === 'chat') {
  if (!message) {
    console.error('Error: Please Provide a message\n\nUsage: chat <message>');
    process.exit(1)
  }

  await main(message);
}

if (cmd === 'doc-chat') {
  await main2();
}

if (cmd === 'doc-assess') {
  const filePath = path.resolve(message)

  if (!existsSync(filePath)) {
    console.error(`File [${message}] does not exist`);
    console.error(`  > Full Path: ${filePath}`)
    process.exit(1);
  }

  const data = readFileSync(filePath, "utf-8");

  const markdownParser = new MarkdownNodeParser();
  const document = new Document({ text: data });
  const tokens = markdownParser.getNodesFromDocuments([document]);

  writeFileSync(
    'nodes.json',
    JSON.stringify(tokens, null, 2),
    'utf-8'
  );

  // const system: ChatMessage = { role: 'system', content: `You are an AI Assistant specializing in processing documents and creating logical chunks.  Take the following document input and output a revised format which optimizes the document for storage in a Vector Database. Your response should simply be the updated organization of the file itself.  DO NOT ADD ANY CONVERSATIONAL TEXT to the output!` };
  const prompt: ChatMessage = { role: 'user', content: RAG_LLM(data) };

  const response = await chat(prompt);

  writeFileSync(
    'test.txt', 
    `System:Prompt: ${prompt.content.split('\n').slice(0,8).join('\n')}\n\n...\n\nResponse: ${response.message.content}`,
    {
      encoding: 'utf-8'
    }
  );
}


saveDB();




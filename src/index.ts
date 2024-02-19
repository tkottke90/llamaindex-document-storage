import { readFileSync, existsSync, writeFileSync } from 'fs';
import "./config.js";
import { chat, serviceContext } from "./llm.js";
import { timer } from "./utils/timing.js";
import { ChatMessage, Document, MarkdownNodeParser, VectorStoreIndex, storageContextFromDefaults } from "llamaindex";

const nodeParser = new MarkdownNodeParser();
const storageContext = await storageContextFromDefaults({
  persistDir: "./index-store",
});

function markdownParser(document: Document) {
  const nodes = nodeParser.getNodesFromDocuments([document]);

  return nodes;
}

async function main2() {
  console.log(`> [${new Date().toISOString()}] Loading Document`);
  // Load essay from abramov.txt in Node
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
      query: "What features does a fighter get at level 2?",
      stream: true,
    });
    const r = t();

    console.log();
    for await (const chunk of response) {
      process.stdout.write(chunk.response);
    }

    console.log(`> [${new Date().toISOString()}] Success Duration: ${r.sec} sec [${r.ms} ms]`);

    console.log(`> [${new Date().toISOString()}] Query Complete`);

    // Output response
    console.log(`
================
>   Response   <
================

${response}
`);
  } catch (err) {
    const r = t();

    console.log(`> [${new Date().toISOString()}] Failed Duration: ${r.sec} sec [${r.ms} ms]`);

    throw err;
  }
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
  const message: ChatMessage = { role: 'user', content: prompt };

  db.messages.push(message);

  const response = await chat(message);

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

saveDB();

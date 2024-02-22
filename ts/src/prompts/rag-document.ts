export const RAG_LLM = (document: string) => `
Review the following markdown document and identify the headers.  Output the headers as a nested list

Here is the document:
${document}
`;
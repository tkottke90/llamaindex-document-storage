export const preprocessClassPrompt = (context_str: string) => `
Input Document: A Markdown document containing the rules and mechanics of a TTRPG game.

Task: Given the input document, split it into logical chunks that respect the concept of "Level" and highlight specific keywords such as "dice," "books," and "pages." The output should be a new document that includes all the important information from the input document, reorganized in a way that focuses on character level.

To achieve this, I will ask your Language Modeling model to:

1. Identify and group together related concepts within the input document, such as character abilities, spells, or combat mechanics.
2. Use the identified keywords and phrases to create a new document that organizes the information in a way that respects the idea of "Level," with each section focusing on a different character experience level.
3. Prioritize formatting the output in a clear and easy-to-read manner, such as using bullet points or short paragraphs.
4. Include all relevant information from the input document, including any important details about characters, spells, or other game mechanics.

Below is the document:
---------------------
${context_str}
---------------------
`;
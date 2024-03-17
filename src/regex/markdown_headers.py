# Markdown Header pattern
#   Pattern Explanation:
#   -  ^: Start of string or line anchor.
#   -  (\#{1,6}\s+[^\r\n]+): Matches one to six # characters followed by whitespace and then a series of non-newline characters. This captures the header text in capture group 1.
#   -  ([\s\S]*?): Matches any number of whitespace or non-whitespace characters (including newline characters) in a non-greedy manner. This captures the sub-text in capture group 2.
#   -  (?=\#|\Z): A positive lookahead assertion that matches if the next character is # or if it's the end of the string. This ensures that we only match the entire header and sub-text when we find a new header or the end of the string, rather than just matching part of a header or sub-text.

def markdownHeaderRegex(depth: int):
  if (depth < 1 or depth > 6):
    raise TypeError(f'Markdown only supports 1-6 header depths, Got [{depth}]')

  return r'^(\#{' + str(depth) + r'}\s+[^\r\n]+)([\s\S]*?)(?=\#|\Z)'
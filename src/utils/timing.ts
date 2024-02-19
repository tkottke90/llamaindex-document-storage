export const NS_PER_SEC = 1e9;
export const NS_TO_MS = 1e6;

export function timer() {
  const start = process.hrtime();

  return () => {
    const diff = process.hrtime(start);
    const nanoSecDuration = diff[0] * NS_PER_SEC + diff[1]
    const miliSecDuration = nanoSecDuration / NS_TO_MS; 

    return {
      ms: miliSecDuration,
      sec: (miliSecDuration / 1000).toFixed(),
      min: (miliSecDuration / 1000 * 60).toFixed()
    }
  }
}

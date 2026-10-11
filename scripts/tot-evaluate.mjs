import {ToTSafetyKernel} from '../vendor/tot/tot-safety-kernel.mjs';
let text = '';
for await (const chunk of process.stdin) {
  text += chunk;
  if (Buffer.byteLength(text) > 65536) throw new Error('INPUT_BOUND');
}
console.log(JSON.stringify(new ToTSafetyKernel().evaluate(JSON.parse(text))));

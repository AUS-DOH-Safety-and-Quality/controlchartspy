import typescript from '@rollup/plugin-typescript';
import nodeResolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import json from '@rollup/plugin-json';
import terser from '@rollup/plugin-terser';
// Core's package exports do not expose its rollup config
import bundleConfig from './node_modules/powerbi-visuals-core/config/rollup.mjs';

const vendor = '../src/controlchartspy/_vendor';

export default bundleConfig({ typescript, nodeResolve, commonjs, json, terser }, {
  ccCore: [`${vendor}/ccCore.min.js`],
  spc: [`${vendor}/PBISPC.min.js`],
  funnel: [`${vendor}/PBIFUN.min.js`],
  ccHeadless: [`${vendor}/ccHeadless.min.js`],
  minidom: [`${vendor}/minidom.min.js`]
});

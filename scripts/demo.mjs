import { readFile } from "node:fs/promises";
import { analyzeTopic } from "../src/core.js";

const loadJson = async (relativePath) => JSON.parse(await readFile(new URL(relativePath, import.meta.url), "utf8"));
const topicData = await loadJson("../data/sample-topics.json");
const policyData = await loadJson("../data/policies.json");
const report = analyzeTopic(topicData.topics[0], policyData.policies);
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);

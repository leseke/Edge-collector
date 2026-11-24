import test from "node:test";
import assert from "node:assert/strict";
import {wizardArticles} from "../src/catalyst-parser.mjs";
test("canonical publisher articles are deduplicated, navigation and external links rejected",()=>{
 const html='<a href="/en/news/announcements/test-release?ref=home"><span>New special collection announced</span></a><a href="https://magic.wizards.com/en/news/announcements/test-release#top">Duplicate announcement</a><a href="https://example.org/en/news/announcements/fake">Untrusted external announcement</a><a href="/en/news">Browse all recent publications</a>';
 assert.deepEqual(wizardArticles(html),[{url:"https://magic.wizards.com/en/news/announcements/test-release",title:"New special collection announced"}]);
});
test("empty and non-text article links do not invent discoveries",()=>{
 assert.deepEqual(wizardArticles('<a href="/en/news/feature/special"><img src="x"></a>'),[]);
 assert.deepEqual(wizardArticles(""),[]);
});

import test from "node:test";
import assert from "node:assert/strict";
import {publisherMetadata} from "../src/catalyst-metadata.mjs";
test("reads publisher metadata and preserves unknown fields",()=>{
 const now=new Date("2026-11-25T00:00:00Z");
 const html='<meta content="New collection &amp; cards" property="og:title"><meta name="description" content="Publisher description"><meta property="article:published_time" content="2026-11-24T10:00:00Z">';
 assert.deepEqual(publisherMetadata(html,now),{headline:"New collection & cards",description:"Publisher description",publishedAt:"2026-11-24T10:00:00.000Z"});
 assert.deepEqual(publisherMetadata("",now),{headline:null,description:null,publishedAt:null});
 assert.equal(publisherMetadata('<meta property="article:published_time" content="2027-01-01">',now).publishedAt,null);
});

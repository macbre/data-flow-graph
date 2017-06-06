# database-flow-graph
Takes SQL logs and **visualizes how your data flow through the database** allowing you quickly to identify **which parts of your code inserts / updates / deletes / reads data from specific DB tables**. This can even be extended to handle messages queues pops and pushes (Redis, RabbitMQ, [`Scribe`](https://github.com/facebookarchive/scribe). ...).

# [Live demo](https://macbre.github.io/database-flow-graph/)

## `dataflow.tsv`

Visualization is generated for a TSV file with the following format:

```
(source node)\t(edge label)\t(target node)\t(edge weight - optional)
```

### Example

```tsv
sphinx:products getSnippet      Elecena\Services\Sphinx 0.0127
mysql:products  _select mq/request.php  0.0313
sphinx:products getKeywords     Elecena\Services\Sphinx 0.0323
sphinx:products getProductsForTags      Elecena\Services\Sphinx 0.0166
mysql:products  getLastChanges  StatsController 0.0003
currency.php    _       mysql:products  0.0000
sphinx:products products        Elecena\Services\Search 0.0126
mysql:products  getImagesToFetch        ImageBot        0.0008
mysql:products  _describe       mq/request.php  0.0007
sphinx:products getIndexCount   Elecena\Services\Sphinx 0.0000
mq/request.php  _update mysql:products  1.0000
ShopsUpdateScript       run     mysql:products  0.0019
mq/request.php  _insert mysql:products  0.0014
mysql:products  run     ShopsUpdateScript       0.0055
sphinx:products rebuildStats    StatsController 0.0004
mysql:products  newFromIds      Elecena\Models\Product  0.0483
sphinx:products getLastChanges  StatsController 0.0003
ImageBot        fetchImage      mysql:products  0.0009
```

> Node names can by categorized by adding a `label` followed by `:`, e.g. `mysql:table`

## Generating TSV file for data flow

You can write your own tool to analyze logs. It just needs to emit TSV file that matches the above format. 

[`sources/elasticsearch/logs2dataflow.py`](https://github.com/macbre/database-flow-graph/blob/master/sources/elasticsearch/logs2dataflow.py) is here as an example - it was used to generate TSV for a [demo](https://macbre.github.io/database-flow-graph/) of this tool. 24 hours of logs from [elecena.pl](https://elecena.pl/ ) were analyzed (1mm+ of SQL queries).

## Links

* [vis.js](https://github.com/almende/vis) for visualization ([a graph example](http://etn.io/))
* [Interactive & Dynamic Force-Directed Graphs with D3](https://medium.com/ninjaconcept/interactive-dynamic-force-directed-graphs-with-d3-da720c6d7811)
* [d3.js curved links graph](https://bl.ocks.org/mbostock/4600693)
* [Bi-directional hierarchical sankey diagram](http://bl.ocks.org/Neilos/584b9a5d44d5fe00f779)

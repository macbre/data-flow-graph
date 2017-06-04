# database-flow-graph
Takes SQL logs and visualizes how your data flow through the database.

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

## Links

* [vis.js](https://github.com/almende/vis) for visualization ([a graph example](http://etn.io/))
* [Interactive & Dynamic Force-Directed Graphs with D3](https://medium.com/ninjaconcept/interactive-dynamic-force-directed-graphs-with-d3-da720c6d7811)
* [d3.js curved links graph](https://bl.ocks.org/mbostock/4600693)
* [Bi-directional hierarchical sankey diagram](http://bl.ocks.org/Neilos/584b9a5d44d5fe00f779)

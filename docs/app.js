'use strict';

var svg, tooltip, biHiSankey, path, defs, colorScale, highlightColorScale, isTransitioning;

var OPACITY = {
    NODE_DEFAULT: 0.9,
    NODE_FADED: 0.1,
    NODE_HIGHLIGHT: 0.8,
    LINK_DEFAULT: 0.6,
    LINK_FADED: 0.05,
    LINK_HIGHLIGHT: 0.9
  },
  TYPES = [],
  TYPE_COLORS = ["#1b9e77", "#d95f02", "#a5a0e3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d"],
  TYPE_HIGHLIGHT_COLORS = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494"],
  LINK_COLOR = "#666",
  INFLOW_COLOR = "#2E86D1",
  OUTFLOW_COLOR = "#D63028",
  NODE_WIDTH = 30,
  COLLAPSER = {
    RADIUS: NODE_WIDTH / 2,
    SPACING: 2
  },
  OUTER_MARGIN = 50,
  MARGIN = {
    TOP: 2 * (COLLAPSER.RADIUS + OUTER_MARGIN),
    RIGHT: OUTER_MARGIN,
    BOTTOM: OUTER_MARGIN,
    LEFT: OUTER_MARGIN
  },
  TRANSITION_DURATION = 400,
  HEIGHT = document.body.clientHeight - MARGIN.TOP - MARGIN.BOTTOM - 20,
  WIDTH = document.body.clientWidth - MARGIN.LEFT - MARGIN.RIGHT - 120,
  LAYOUT_INTERATIONS = 32,
  REFRESH_INTERVAL = 7000;

var formatNumber = function (d) {
  var numberFormat = d3.format(",.0f"); // zero decimal places
  return "£" + numberFormat(d);
},

formatFlow = function (d) {
  var flowFormat = d3.format(",.0f"); // zero decimal places with sign
  return "£" + flowFormat(Math.abs(d)) + (d < 0 ? " CR" : " DR");
},

// Used when temporarily disabling user interractions to allow animations to complete
disableUserInterractions = function (time) {
  isTransitioning = true;
  setTimeout(function(){
    isTransitioning = false;
  }, time);
},

hideTooltip = function () {
  return tooltip.transition()
    .duration(TRANSITION_DURATION)
    .style("opacity", 0);
},

showTooltip = function () {
  return tooltip
    .style("left", d3.event.pageX + "px")
    .style("top", d3.event.pageY + 15 + "px")
    .transition()
      .duration(TRANSITION_DURATION)
      .style("opacity", 1);
};

colorScale = d3.scale.ordinal().domain(TYPES).range(TYPE_COLORS),
highlightColorScale = d3.scale.ordinal().domain(TYPES).range(TYPE_HIGHLIGHT_COLORS),

svg = d3.select("#chart").append("svg")
        .attr("width", WIDTH + MARGIN.LEFT + MARGIN.RIGHT)
        .attr("height", HEIGHT + MARGIN.TOP + MARGIN.BOTTOM)
      .append("g")
        .attr("transform", "translate(" + MARGIN.LEFT + "," + MARGIN.TOP + ")");

svg.append("g").attr("id", "links");
svg.append("g").attr("id", "nodes");
svg.append("g").attr("id", "collapsers");

tooltip = d3.select("#chart").append("div").attr("id", "tooltip");

tooltip.style("opacity", 0)
    .append("p")
      .attr("class", "value");

biHiSankey = d3.biHiSankey();

// Set the biHiSankey diagram properties
biHiSankey
  .nodeWidth(NODE_WIDTH)
  .nodeSpacing(32)
  .linkSpacing(5)
  .arrowheadScaleFactor(0.25) // Specifies that 0.5 of the link's stroke WIDTH should be allowed for the marker at the end of the link.
  .size([WIDTH, HEIGHT]);

path = biHiSankey.link().curvature(0.45);

defs = svg.append("defs");

defs.append("marker")
  .style("fill", LINK_COLOR)
  .attr("id", "arrowHead")
  .attr("viewBox", "0 0 6 10")
  .attr("refX", "1")
  .attr("refY", "5")
  .attr("markerUnits", "strokeWidth")
  .attr("markerWidth", "1")
  .attr("markerHeight", "1")
  .attr("orient", "auto")
  .append("path")
    .attr("d", "M 0 0 L 1 0 L 6 5 L 1 10 L 0 10 z");

defs.append("marker")
  .style("fill", OUTFLOW_COLOR)
  .attr("id", "arrowHeadInflow")
  .attr("viewBox", "0 0 6 10")
  .attr("refX", "1")
  .attr("refY", "5")
  .attr("markerUnits", "strokeWidth")
  .attr("markerWidth", "1")
  .attr("markerHeight", "1")
  .attr("orient", "auto")
  .append("path")
    .attr("d", "M 0 0 L 1 0 L 6 5 L 1 10 L 0 10 z");

defs.append("marker")
  .style("fill", INFLOW_COLOR)
  .attr("id", "arrowHeadOutlow")
  .attr("viewBox", "0 0 6 10")
  .attr("refX", "1")
  .attr("refY", "5")
  .attr("markerUnits", "strokeWidth")
  .attr("markerWidth", "1")
  .attr("markerHeight", "1")
  .attr("orient", "auto")
  .append("path")
    .attr("d", "M 0 0 L 1 0 L 6 5 L 1 10 L 0 10 z");

function update () {
  var link, linkEnter, node, nodeEnter, collapser, collapserEnter;

  function dragmove(node) {
    node.x = Math.max(0, Math.min(WIDTH - node.width, d3.event.x));
    node.y = Math.max(0, Math.min(HEIGHT - node.height, d3.event.y));
    d3.select(this).attr("transform", "translate(" + node.x + "," + node.y + ")");
    biHiSankey.relayout();
    svg.selectAll(".node").selectAll("rect").attr("height", function (d) { return d.height; });
    link.attr("d", path);
  }

  function containChildren(node) {
    node.children.forEach(function (child) {
      child.state = "contained";
      child.parent = this;
      child._parent = null;
      containChildren(child);
    }, node);
  }

  function expand(node) {
    node.state = "expanded";
    node.children.forEach(function (child) {
      child.state = "collapsed";
      child._parent = this;
      child.parent = null;
      containChildren(child);
    }, node);
  }

  function collapse(node) {
    node.state = "collapsed";
    containChildren(node);
  }

  function restoreLinksAndNodes() {
    link
      .style("stroke", LINK_COLOR)
      .style("marker-end", function () { return 'url(#arrowHead)'; })
      .transition()
        .duration(TRANSITION_DURATION)
        .style("opacity", OPACITY.LINK_DEFAULT);

    node
      .selectAll("rect")
        .style("fill", function (d) {
          d.color = colorScale(d.type.replace(/ .*/, ""));
          return d.color;
        })
        .style("stroke", function (d) {
          return d3.rgb(colorScale(d.type.replace(/ .*/, ""))).darker(0.1);
        })
        .style("fill-opacity", OPACITY.NODE_DEFAULT);

    node.filter(function (n) { return n.state === "collapsed"; })
      .transition()
        .duration(TRANSITION_DURATION)
        .style("opacity", OPACITY.NODE_DEFAULT);
  }

  function showHideChildren(node) {
    disableUserInterractions(2 * TRANSITION_DURATION);
    hideTooltip();
    if (node.state === "collapsed") { expand(node); }
    else { collapse(node); }

    biHiSankey.relayout();
    update();
    link.attr("d", path);
    restoreLinksAndNodes();
  }

  function highlightConnected(g) {
    link.filter(function (d) { return d.source === g; })
      .style("marker-end", function () { return 'url(#arrowHeadInflow)'; })
      .style("stroke", OUTFLOW_COLOR)
      .style("opacity", OPACITY.LINK_DEFAULT);

    link.filter(function (d) { return d.target === g; })
      .style("marker-end", function () { return 'url(#arrowHeadOutlow)'; })
      .style("stroke", INFLOW_COLOR)
      .style("opacity", OPACITY.LINK_DEFAULT);
  }

  function fadeUnconnected(g) {
    link.filter(function (d) { return d.source !== g && d.target !== g; })
      .style("marker-end", function () { return 'url(#arrowHead)'; })
      .transition()
        .duration(TRANSITION_DURATION)
        .style("opacity", OPACITY.LINK_FADED);

    node.filter(function (d) {
      return (d.name === g.name) ? false : !biHiSankey.connected(d, g);
    }).transition()
      .duration(TRANSITION_DURATION)
      .style("opacity", OPACITY.NODE_FADED);
  }

  link = svg.select("#links").selectAll("path.link")
    .data(biHiSankey.visibleLinks(), function (d) { return d.id; });

  link.transition()
    .duration(TRANSITION_DURATION)
    .style("stroke-WIDTH", function (d) { return Math.max(1, d.thickness); })
    .attr("d", path)
    .style("opacity", OPACITY.LINK_DEFAULT);


  link.exit().remove();


  linkEnter = link.enter().append("path")
    .attr("class", "link")
    .style("fill", "none");

  linkEnter.on('mouseenter', function (d) {
    if (!isTransitioning) {
      showTooltip().select(".value").text(function () {
        // find link metadata
        var meta = exampleLinks.find(function(link) {
           return link.id == d.id;
        });

	var label = meta.name;
	if (meta.metadata) {
		label += "\n" + meta.metadata;
	}

        if (d.direction > 0) {
          return label + "\n" + d.source.name + " \u21D2 " + d.target.name;
        }
        return label + "\n" + d.target.name + " \u21D0 " + d.source.name;
      });

      d3.select(this)
        .style("stroke", LINK_COLOR)
        .transition()
          .duration(TRANSITION_DURATION / 2)
          .style("opacity", OPACITY.LINK_HIGHLIGHT);
    }
  });

  linkEnter.on('mouseleave', function () {
    if (!isTransitioning) {
      hideTooltip();

      d3.select(this)
        .style("stroke", LINK_COLOR)
        .transition()
          .duration(TRANSITION_DURATION / 2)
          .style("opacity", OPACITY.LINK_DEFAULT);
    }
  });

  linkEnter.sort(function (a, b) { return b.thickness - a.thickness; })
    .classed("leftToRight", function (d) {
      return d.direction > 0;
    })
    .classed("rightToLeft", function (d) {
      return d.direction < 0;
    })
    .style("marker-end", function () {
      return 'url(#arrowHead)';
    })
    .style("stroke", LINK_COLOR)
    .style("opacity", 0)
    .transition()
      .delay(TRANSITION_DURATION)
      .duration(TRANSITION_DURATION)
      .attr("d", path)
      .style("stroke-WIDTH", function (d) { return Math.max(1, d.thickness); })
      .style("opacity", OPACITY.LINK_DEFAULT);


  node = svg.select("#nodes").selectAll(".node")
      .data(biHiSankey.collapsedNodes(), function (d) { return d.id; });


  node.transition()
    .duration(TRANSITION_DURATION)
    .attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; })
    .style("opacity", OPACITY.NODE_DEFAULT)
    .select("rect")
      .style("fill", function (d) {
        d.color = colorScale(d.type.replace(/ .*/, ""));
        return d.color;
      })
      .style("stroke", function (d) { return d3.rgb(colorScale(d.type.replace(/ .*/, ""))).darker(0.1); })
      .style("stroke-WIDTH", "1px")
      .attr("height", function (d) { return d.height; })
      .attr("width", biHiSankey.nodeWidth());


  node.exit()
    .transition()
      .duration(TRANSITION_DURATION)
      .attr("transform", function (d) {
        var collapsedAncestor, endX, endY;
        collapsedAncestor = d.ancestors.filter(function (a) {
          return a.state === "collapsed";
        })[0];
        endX = collapsedAncestor ? collapsedAncestor.x : d.x;
        endY = collapsedAncestor ? collapsedAncestor.y : d.y;
        return "translate(" + endX + "," + endY + ")";
      })
      .remove();


  nodeEnter = node.enter().append("g").attr("class", "node");

  nodeEnter
    .attr("transform", function (d) {
      var startX = d._parent ? d._parent.x : d.x,
          startY = d._parent ? d._parent.y : d.y;
      return "translate(" + startX + "," + startY + ")";
    })
    .style("opacity", 1e-6)
    .transition()
      .duration(TRANSITION_DURATION)
      .style("opacity", OPACITY.NODE_DEFAULT)
      .attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; });

  nodeEnter.append("text");
  nodeEnter.append("rect")
    .style("fill", function (d) {
      d.color = colorScale(d.type.replace(/ .*/, ""));
      return d.color;
    })
    .style("stroke", function (d) {
      return d3.rgb(colorScale(d.type.replace(/ .*/, ""))).darker(0.1);
    })
    .style("stroke-WIDTH", "1px")
    .attr("height", function (d) { return d.height; })
    .attr("width", biHiSankey.nodeWidth())
    .attr("rx", function(d) { return d.type ? 5 : 0 })
    .attr("rx", function(d) { return d.type ? 5 : 0 });

  node.on("mouseenter", function (g) {
    if (!isTransitioning) {
      restoreLinksAndNodes();
      highlightConnected(g);
      fadeUnconnected(g);

      d3.select(this).select("rect")
        .style("fill", function (d) {
          d.color = d.netFlow > 0 ? INFLOW_COLOR : OUTFLOW_COLOR;
          return d.color;
        })
        .style("stroke", function (d) {
          return d3.rgb(d.color).darker(0.1);
        })
        .style("fill-opacity", OPACITY.LINK_DEFAULT);

      tooltip
        .style("left", g.x + MARGIN.LEFT + "px")
        .style("top", g.y + g.height + MARGIN.TOP + 15 + "px")
        .transition()
          .duration(TRANSITION_DURATION)
          .style("opacity", 1).select(".value")
          .text(function () {
            return g.name; //  + "\nNet flow: " + formatFlow(g.netFlow) + additionalInstructions;
          });
    }
  });

  node.on("mouseleave", function () {
    if (!isTransitioning) {
      hideTooltip();
      restoreLinksAndNodes();
    }
  });

  node.filter(function (d) { return d.children.length; })
    .on("dblclick", showHideChildren);

  // allow nodes to be dragged to new positions
  node.call(d3.behavior.drag()
    .origin(function (d) { return d; })
    .on("dragstart", function () { this.parentNode.appendChild(this); })
    .on("drag", dragmove));

  // add in the text for the nodes
  node.filter(function (d) { return d.value !== 0; })
    .select("text")
      .attr("x", -6)
      .attr("y", function (d) { return d.height / 2; })
      .attr("dy", ".35em")
      .attr("text-anchor", "end")
      .attr("transform", null)
      .attr("fill", "#ddd")
      .text(function (d) { return d.name; })
    .filter(function (d) { return d.x < WIDTH / 2; })
      .attr("x", 6 + biHiSankey.nodeWidth())
      .attr("text-anchor", "start");


  collapser = svg.select("#collapsers").selectAll(".collapser")
    .data(biHiSankey.expandedNodes(), function (d) { return d.id; });


  collapserEnter = collapser.enter().append("g").attr("class", "collapser");

  collapserEnter.append("circle")
    .attr("r", COLLAPSER.RADIUS)
    .style("fill", function (d) {
      d.color = colorScale(d.type.replace(/ .*/, ""));
      return d.color;
    });

  collapserEnter
    .style("opacity", OPACITY.NODE_DEFAULT)
    .attr("transform", function (d) {
      return "translate(" + (d.x + d.width / 2) + "," + (d.y + COLLAPSER.RADIUS) + ")";
    });

  collapserEnter.on("dblclick", showHideChildren);

  collapser.select("circle")
    .attr("r", COLLAPSER.RADIUS);

  collapser.transition()
    .delay(TRANSITION_DURATION)
    .duration(TRANSITION_DURATION)
    .attr("transform", function (d, i) {
      return "translate("
        + (COLLAPSER.RADIUS + i * 2 * (COLLAPSER.RADIUS + COLLAPSER.SPACING))
        + ","
        + (-COLLAPSER.RADIUS - OUTER_MARGIN)
        + ")";
    });

  collapser.on("mouseenter", function (g) {
    if (!isTransitioning) {
      showTooltip().select(".value")
        .text(function () {
          return g.name + "\n(Double click to collapse)";
        });

      var highlightColor = highlightColorScale(g.type.replace(/ .*/, ""));

      d3.select(this)
        .style("opacity", OPACITY.NODE_HIGHLIGHT)
        .select("circle")
          .style("fill", highlightColor);

      node.filter(function (d) {
        return d.ancestors.indexOf(g) >= 0;
      }).style("opacity", OPACITY.NODE_HIGHLIGHT)
        .select("rect")
          .style("fill", highlightColor);
    }
  });

  collapser.on("mouseleave", function (g) {
    if (!isTransitioning) {
      hideTooltip();
      d3.select(this)
        .style("opacity", OPACITY.NODE_DEFAULT)
        .select("circle")
          .style("fill", function (d) { return d.color; });

      node.filter(function (d) {
        return d.ancestors.indexOf(g) >= 0;
      }).style("opacity", OPACITY.NODE_DEFAULT)
        .select("rect")
          .style("fill", function (d) { return d.color; });
    }
  });

  collapser.exit().remove();

}

// @see https://stackoverflow.com/a/14438954
function onlyUnique(value, index, self) {
    return self.indexOf(value) === index;
}

// load TSV example
var dataflow, tsvData, columns, nodes, links;

dataflow = document.getElementById('dataflow');

tsvData = dataflow.text.trim().split("\n");
columns = tsvData.map(function(line) {
	return line.trim().split("\t");
});

// nodes are in columns 1st and 3rd
nodes = columns.
	sort(function(a, b) {
		return b[3] - a[3];
	}).
	map(function(line) {return line[0]}).
	concat(
		columns.map(function(line) {return line[2];})
	).
	filter(onlyUnique)

// sort nodes alphabetically? (DB on the left, code on the right)
//nodes = nodes.sort();

// sort, but ignoring the label prefix
/**
nodes = nodes.sort(function(a,b) {
	return a.split(':').pop().toLowerCase() < b.split(':').pop().toLowerCase() ? -1 : 1;
});
**/

console.log(nodes);

// prepare nodes and links for biHiSankey library
var exampleNodes = nodes.map(function(node, iter) {
	var type = '',
		pos = node.indexOf(':');

	if (pos > -1) {
		type = node.substring(0, pos);
		// node = node.substring(pos+1);
	}

	// push to TYPES
	if (TYPES.indexOf(type) === -1) {
		TYPES.push(type);
	}

	return {
		type: type,
		id: iter,
		name: node
	};
});

var exampleLinks = columns.map(function(line) {
	var weight = line[3] && parseFloat(line[3]) || 1;

	weight = Math.max(weight, 0.001);

	// scale using log10
	weight = Math.log10(weight * 10000) / 10;

	return {
		source: nodes.indexOf(line[0]),
		target: nodes.indexOf(line[2]),
		value: weight,
		name: line[1],
		metadata: line[4] || ''
	};
});

/**
var exampleNodes = [
  {"type":"mysql","id":1,"name":"Liabilities"},
  {"type":"sphinx","id":2,"name":"Expenses"},
  {"type": "", "id":3,"name":"Foo\\Name"},
]

var exampleLinks = [
  {"source":1, "target":2, "value": 1, "name": "pushData"},
  {"source":3, "target":2, "value": 0.03, "name": "pushData"},
]
**/

console.log(exampleNodes, exampleLinks);

// @se https://github.com/Neilos/bihisankey
biHiSankey
  .nodes(exampleNodes)
  .links(exampleLinks)
  .initializeNodes(function (node) {
    node.state = node.parent ? "contained" : "collapsed";
  })
  .layout(LAYOUT_INTERATIONS);

disableUserInterractions(2 * TRANSITION_DURATION);

update();

// set subtitle
var subtitle = dataflow.getAttribute('data-name');

if (subtitle) {
	document.getElementById('subtitle').innerHTML = subtitle;
}

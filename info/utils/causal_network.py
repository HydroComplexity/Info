'''
This script is used for creating a causal network, which is able to:
(1) find the parent(s) and neighbor(s) of a node
(2) check whether two nodes are linked with a directed link or an undirected link
(3) find the causal path between two nodes
(4) find the conditions for calculating the momentary information transfer (MIT) between two nodes
(5) find the conditions for calculating the momentary partial information decomposition (MPID) between two sources and a target
(6) find the elements for calculating the accumulated information transfer

Ref:
Runge PRE (2015)
Jiang and Kumar PRE (2018)

class causal_network()
    __init__()
    search_parents()
    search_paths()
    check_links()
    search_mit_condition()
    search_mitp_condition()
    search_mpid_condition()
    search_mpid_set_condition()
    search_cit_components()

convert_nodes_to_listofset()
get_node_number()
is_neighbor()
get_node_set()
get_path_nodes_and_their_parents()
get_causal_contemp_paths()
get_parents_from_nodes()
get_neighbors_from_nodes()
unique()
intersect()
union()
exclude_intersection()

'''

from copy import deepcopy
import networkx as nx
import numpy as np


class causal_network(object):
    """A class for causal network."""

    def __init__(self, causalDict, lagfuncs=None, taumax=6):
        """
        Input:
        causalDict -- dictionary of causal relationships, where
                      the keys are the variable at t time [int]
                      the values are the parents of the corresponding node [list of sets].
                      e.g., {0: [(0,-1), (1,-1)], 1: [(0,-2), (1,-1)]}
        lagfuncs   -- the coupling strength [used for the weights of edges]
        taumax -- the maximum time lag [int]

        """
        var    = causalDict.keys()
        nvar   = len(var)

        # Get the equally assigned lagfunctions if it does not exist
        if lagfuncs is None:
            lagfuncs = np.ones([nvar,nvar,taumax+1])
            print 1
        else:
            lagfuncs = np.copy(lagfuncs)

        self.causalDict = causalDict
        self.taumax     = taumax
        self.originalLagfuncs = np.copy(lagfuncs)

        # Create an empty directed graph
        g = nx.DiGraph()

        # Assign all the nodes into the directed graph
        nnodes = nvar*(taumax+1)
        g.add_nodes_from(range(nnodes))

        # Get the offset of the lags so that all the weights are nonnegative
        offset = lagfuncs.min() if lagfuncs.min() < 0 else 0
        lagfuncs -= offset

        # Assign all the edges
        for i in range(taumax+1):
            gap           = nvar*i
            involved_nodes = range(gap, gap+nvar)
            for j in range(nvar):
                end = involved_nodes[j]
                for parent in causalDict[j]:
                    we = lagfuncs[parent[0], j, abs(parent[1])]
                    # Add the edge
                    start = get_node_number(parent, nvar, gap)
                    if start < nnodes:
                        g.add_edge(start, end, weight=we)

        # Assign the weights
        weights = np.zeros([nnodes, nnodes])
        for (start, end) in g.edges():
            if start < nnodes:
                weights[start, end] = g[start][end]['weight']

        self.var     = var
        self.nvar    = nvar
        self.nnodes  = nnodes
        self.gnnodes = g.number_of_nodes()
        self.g       = g
        self.offset  = offset
        self.weights = weights

    def __check_node(self, target):
        """
        Check whether the target node is in the valid graph by fulfilling the following conditions:
            (1) var_index is within self.var
            (2) lag is smaller than and equal to taumax
        Input:
        target -- the target node [set (var_index, lag)]

        """
        if target[0] not in self.var:
            raise Exception("The target variable %d is not in the valid variable set!" % target[0])

        if target[1] > self.taumax:
            raise Exception("The time step of the target node %d is larger than the taumax!" % target[1])

    def search_parents(self, target, verbosity=1):
        """
        Find the parent(s) of a node.

        Input:
        target -- the target node [set (var_index, lag)]

        """
        g, nvar = self.g, self.nvar

        # Check whether the node is in the causal network
        self.__check_node(target)

        # Get the node number
        tnode = get_node_number(target, nvar, 0)

        # Get its parents
        parents = get_parents_from_nodes(g, [tnode])

        if not parents:
            if verbosity == 1:
                print 'No parents and neighbors for the node:', target
            return []
        else:
            return convert_nodes_to_listofset(parents, nvar)

    def search_children(self, target, verbosity=1):
        """
        Find the child(ren) of a node.

        Input:
        target -- the target node [set (var_index, lag)]
        Output:
        {'parents': list of set, 'neighbors': list of set}

        """
        g, nvar = self.g, self.nvar

        # Check whether the node is in the causal network
        self.__check_node(target)

        # Get the node number
        tnode = get_node_number(target, nvar, 0)

        # Get its children
        children = get_children_from_nodes(g, [tnode])

        if not children and verbosity==1:
            print 'No children for the node:'
            print target
            return []
        else:
            return convert_nodes_to_listofset(children, nvar)

    def search_causalpaths(self, source, target, nested=False, verbosity=1):
        """
        Find the causal paths between a source and a target.

        Input:
        source -- the source node [set (var_index, lag)]
        target -- the target node [set (var_index, lag)]
        Output:
        if nested     -- list of paths (each of which is a list of set),
        if not nested -- list of set

        """
        g, nvar = self.g, self.nvar

        # Check whether the node is in the causal network
        self.__check_node(source)
        self.__check_node(target)

        # Get the node number
        snode = get_node_number(source, nvar, 0)
        tnode = get_node_number(target, nvar, 0)

        # Return
        if nested:
            # Get the caual paths
            causalpaths_nest = get_causal_paths(g, snode, tnode, nested=nested)
            return [convert_nodes_to_listofset(path, nvar) for path in causalpaths_nest]
        else:
            # Get the caual paths
            causalpaths      = get_causal_paths(g, snode, tnode, nested=nested)
            return convert_nodes_to_listofset(causalpaths, nvar)

    def check_links(self, source, target, verbosity=1):
        """
        Check whether two nodes are linked with a directed link or a causal path.

        Input:
        source -- the source node [set (var_index, lag)]
        target -- the target node [set (var_index, lag)]
        Output:
        directed link            -- 'directed'
        causal path              -- 'causalpath'
        none of the above        -- None

        """
        # Check whether the link is a directed link or an undirected link
        parents = self.search_parents(target, verbosity=verbosity)
        if source in parents:
            return 'directed'

        # Check whether the link is a causal path or a contemporaneous sidepath
        paths = self.search_causalpaths(source, target, nested=True, verbosity=verbosity)
        if paths:
            return 'causalpath'

        # If none of them is found, return None
        if verbosity==1:
            print '%s and %s are not linked through the following types:' % (source, target)
            print 'directed link and causal path!'
        return None

    def search_mit_condition(self, source, target, transitive=False, verbosity=1):
        """
        Find the conditions for calculating the momentary information transfer (MIT) between between a source and a target
        Input:
        source -- the source node [set (var_index, lag)]
        target -- the target node [set (var_index, lag)]
        transitive -- indicator whether the weighted transitive reduction should be performed [bool]
        Output:
        the condition for MIT [list of sets]

        """
        g, nvar = self.g, self.nvar

        # Check whether the node is in the causal network
        self.__check_node(source)
        self.__check_node(target)

        # Get the node number
        snode = get_node_number(source, nvar, 0)
        tnode = get_node_number(target, nvar, 0)

        # Get the parents of the target node
        pt = get_parents_from_nodes(g, [tnode])

        # Get the condition for MIT
        w1 = get_parents_from_nodes(g, [snode])
        w2 = exclude_intersection(get_parents_from_nodes(g, [tnode]), [snode])
        w = union([w1, w2])

        w = convert_nodes_to_listofset(w, nvar)

        if verbosity:
            print ""
            print "The number of conditions from %s to %s is %d, including:" % (source, target, len(w))
            print w
            print ""

        return w

    def search_mitp_condition(self, source, target, transitive=False, verbosity=1):
        """
        Find the conditions for calculating the momentary information transfer (MIT) between between a source and a target
        Input:
        source -- the source node [set (var_index, lag)]
        target -- the target node [set (var_index, lag)]
        transitive -- indicator whether the weighted transitive reduction should be performed [bool]
        Output:
        the condition for MITP [list of sets]

        """
        g, nvar = self.g, self.nvar

        # Check whether the node is in the causal network
        self.__check_node(source)
        self.__check_node(target)

        # Get the node number
        snode = get_node_number(source, nvar, 0)
        tnode = get_node_number(target, nvar, 0)

        # Get the parents of the target node
        pt = get_parents_from_nodes(g, [tnode])

        linktype = self.check_links(source, target, verbosity=verbosity)

        # Get the condition for MITP
        if linktype is None:
            w = []
            if verbosity == 1:
                print "The two nodes %s and %s are not connected by a causal path!" % (source, target)

        else:                                              # linked by a causal path
            # Get the causal path and the parent(s) of the causal path of the source
            pcpath, cpath = get_path_nodes_and_their_parents(g, snode, tnode)
            w = list(union([pcpath, exclude_intersection(pt, cpath)]))

            # Conduct the weighted transitive reduction on the condition set w if required
            if transitive:
                # Get the descendants/children of the w
                wchild = get_children_from_nodes(g, w)
                # Get the intersection of the descendants and the cpaths
                wchild_cpaths = intersect(wchild, cpath)
                # Get the reduced condition set
                w = self.transitive_reduction(w, wchild_cpaths)

        w = convert_nodes_to_listofset(w, nvar)

        if verbosity:
            print "The link type between %s and %s is %s" % (source, target, linktype)
            print "The number of conditions from %s to %s is %d, including:" % (source, target, len(w))
            print w

        return w

    def search_mpid_condition(self, source1, source2, target, transitive=False, onlyw=True, verbosity=1):
        """
        Find the conditions for calculating the momentary partial information decomposition (MPID) between two sources and a target.

        Input:
        source1  -- the first source node [set (var_index, lag)]
        source2  -- the second source node [set (var_index, lag)]
        target   -- the target node [set (var_index, lag)]
        transitive -- indicator whether the weighted transitive reduction should be performed [bool]
        Output:
        the condition for MPID [list of sets]

        """
        g, nvar = self.g, self.nvar

        # Check whether the node is in the causal network
        self.__check_node(source1)
        self.__check_node(source2)
        self.__check_node(target)

        # Check whether the two sources are linked with the target through causal paths
        linktype1 = self.check_links(source1, target, verbosity=verbosity)
        linktype2 = self.check_links(source2, target, verbosity=verbosity)
        if linktype1 not in ['causalpath', 'directed']:
            if verbosity == 1:
                print "The source %s and the target %s are not linked by a causal path" % (source1, target)
            return []
        if linktype2 not in ['causalpath', 'directed']:
            if verbosity == 1:
                print "The source %s and the target %s are not linked by a causal path" % (source2, target)
            return []

        # Get the node number
        s1node = get_node_number(source1, nvar, 0)
        s2node = get_node_number(source2, nvar, 0)
        tnode  = get_node_number(target, nvar, 0)

        # Get the parents of the target node
        pt = get_parents_from_nodes(g, [tnode])

        # Get the causal path and the parent(s) of the causal path of the two sources
        pcpath1, cpath1 = get_path_nodes_and_their_parents(g, s1node, tnode)
        pcpath2, cpath2 = get_path_nodes_and_their_parents(g, s2node, tnode)

        # Get the conditions for MPID
        w1 = exclude_intersection(pt, union([cpath1, cpath2]))
        w2 = exclude_intersection(pcpath1, cpath2)
        w3 = exclude_intersection(pcpath2, cpath1)
        w = list(union([w1, w2, w3]))

        # Conduct the weighted transitive reduction on the condition set w if required
        cpaths = list(union([cpath1, cpath2]))
        if transitive:
            # Get the descendants/children of the w
            wchild = get_children_from_nodes(g, w)
            # Get the intersection of the descendants and the cpaths
            wchild_cpaths = intersect(wchild, cpaths)
            # Get the reduced condition set
            # print w
            w = self.transitive_reduction(w, wchild_cpaths)

        w = convert_nodes_to_listofset(w, nvar)

        if verbosity:
            print "The number of conditions from %s and %s to %s is %d, including:" % (source1, source2, target, len(w))
            print w

        if onlyw:
            return w
        else:
            cpaths = convert_nodes_to_listofset(cpaths, nvar)
            return w, cpaths


    def search_mpid_set_condition(self, sources1, sources2, target, transitive=False, verbosity=1):
        """
        Find the conditions for calculating the momentary partial information decomposition (MPID) between two sets of sources and a target.

        Input:
        sources1 -- a first list of source nodes [[set (var_index, lag)]]
        sources2 -- a second list of source nodes [[set (var_index, lag)]]
        target   -- the target node [set (var_index, lag)]
        transitive -- indicator whether the weighted transitive reduction should be performed [bool]
        Output:
        the condition for MPID [list of sets]

        """
        g, nvar = self.g, self.nvar

        # Check whether the node is in the causal network
        for src in sources1:
            self.__check_node(src)
        for src in sources2:
            self.__check_node(src)
        self.__check_node(target)

        # Get the sources that are connected with the target through either a directed edge or a causal path
        srcs1, srcs2 = [], []
        for src in sources1:
            linktype1 = self.check_links(src, target, verbosity=verbosity)
            if linktype1 not in ['causalpath', 'directed']:
                if verbosity == 1:
                    print "The source %s and the target %s are not linked by a causal path" % (src, target)
            else:
                srcs1.append(src)
        for src in sources2:
            linktype2 = self.check_links(src, target, verbosity=verbosity)
            if linktype2 not in ['causalpath', 'directed']:
                if verbosity == 1:
                    print "The source %s and the target %s are not linked by a causal path" % (src, target)
            else:
                srcs2.append(src)

        # Get the node numbers
        s1nodes = [get_node_number(src, nvar, 0) for src in srcs1]
        s2nodes = [get_node_number(src, nvar, 0) for src in srcs2]
        tnode   = get_node_number(target, nvar, 0)

        # Get the parents of the target node
        pt = get_parents_from_nodes(g, [tnode])

        # Get the causal path and the parent(s) of the causal path of the two sources
        # 1st set of sources
        pcpaths1, cpaths1 = [], []
        for s1node in s1nodes:
            pcpath1, cpath1 = get_path_nodes_and_their_parents(g, s1node, tnode)
            pcpaths1.append(pcpath1)
            cpaths1.append(cpath1)
        pcpaths1 = unique([node for pcpath in pcpaths1 for node in pcpath])
        cpaths1  = unique([node for cpath in cpaths1 for node in cpath])
        # 2nd set of sources
        pcpaths2, cpaths2 = [], []
        for s2node in s2nodes:
            pcpath2, cpath2 = get_path_nodes_and_their_parents(g, s2node, tnode)
        pcpaths2 = unique([node for pcpath in pcpaths2 for node in pcpath])
        cpaths2  = unique([node for cpath in cpaths2 for node in cpath])

        # Get the conditions for MPID
        w1 = exclude_intersection(pt, union([cpaths1, cpaths2]))
        w2 = exclude_intersection(pcpaths1, cpaths2)
        w3 = exclude_intersection(pcpaths2, cpaths1)
        w = list(union([w1, w2, w3]))

        # Conduct the weighted transitive reduction on the condition set w if required
        cpaths = list(union([cpaths1, cpaths2]))
        if transitive:
            # Get the descendants/children of the w
            wchild = get_children_from_nodes(g, w)
            # Get the intersection of the descendants and the cpaths
            wchild_cpaths = intersect(wchild, cpaths)
            # Get the reduced condition set
            # print w
            w = self.transitive_reduction(w, wchild_cpaths)

        w = convert_nodes_to_listofset(w, nvar)

        if verbosity:
            print "The number of conditions from two sets of source nodes to %s is %d, including:" % (target, len(w))
            print w

        return srcs1, srcs2, w


    def search_bundled_components(self, srcset, target, tau, level=1, transitive=False, returnRemovedEdges=False, verbosity=1):
        """
        Find the elements for calculating the information transfer (CIT) from bundled sources to the target.

        Input:
        srcset -- the first list of source variables [[var_index]]
        target   -- the target node [set (var_index, lag)]
        tau     -- the time lag for separating immediate and distant causal histories
        transitive -- indicator whether the weighted transitive reduction should be performed [bool]
        Output:
        the elements for BCH [list of sets]

        """
        import copy
        g, nvar = self.g, self.nvar
        nsource = len(srcset)
        sources = [(src, -tau) for src in srcset]

        # Check whether the node is in the causal network
        for source in sources:
            self.__check_node(source)
        self.__check_node(target)

        # Get the node number
        snodes = [get_node_number(source, nvar, 0) for source in sources]
        tnode  = get_node_number(target, nvar, 0)

        # Get all the nodes in the immediate causal history
        ichlist = [(src,-i) for src in srcset for i in range(1,tau+1)]
        ich     = [get_node_number(node, nvar, 0) for node in ichlist]

        # Get the parents of the target node
        pt = get_parents_from_nodes(g, [tnode])

        # Get the parents of the target node in the causal paths from the sourcesnew
        pt_list = convert_nodes_to_listofset(pt, nvar)
        ptclist = [node for node in pt_list if node[0] in srcset and node[1] >= -tau]

        # Get the representative distant causala history, w
        w = get_parents_from_nodes(g, ich)
        wlist  = convert_nodes_to_listofset(w, nvar)

        # Keep the nodes only in the distant causal history of srcset
        wlist = [node for node in wlist if node[1] < -tau and node[0] in srcset]
        w = [get_node_number(node, nvar, 0) for node in wlist]

        # Conduct the weighted transitive reduction on w if required
        if transitive:
            # Get the descendants/children of the w
            wchild = get_children_from_nodes(g, w)
            # Get the intersection of the descendants and the immediate causal history
            wchild_ich = intersect(wchild, ich)
            # Get the reduced condition set
            # print w
            if returnRemovedEdges:
                w, edges = self.transitive_reduction(w, wchild_ich, True)
                edges = [(get_node_set(edge[0],nvar), get_node_set(edge[1],nvar)) for edge in edges]
            else:
                w = self.transitive_reduction(w, wchild_ich)

        wlist  = convert_nodes_to_listofset(w, nvar)
        # ptc = convert_nodes_to_listofset(ptc, nvar)

        # Get the remaining parents of the target
        ptrlist = list(set(pt_list)-set(ptclist))
        if verbosity:
            print("the parents of the target in the remaining variables:")
            print(ptrlist)

        # Get the condition set in the remaining variables, f, based on the approximation level
        if level == 0 or len(srcset) == nvar:  # 0 order approximation or srcset1 and srcset2 occupy all the variables
            flist, pwlist, pptclist = [], [], []
        elif level == 1:  # 1st order approximation: only consider the remaining parents of the target
            pwlist, pptclist = [], []
            flist = deepcopy(ptrlist)
        elif level == 2:  # 2nd order approximation: consider both the parents of ptc and w and the remaining parents of the target
            pwlist   = [node2 for node1 in wlist for node2 in self.search_parents(node1) if node2[0] not in srcset]
            pptclist = [node2 for node1 in ptclist for node2 in self.search_parents(node1) if node2[0] not in srcset]
            flist    = list(set(pwlist+pptclist+ptrlist))

        # Conduct the weighted transitive reduction on pptc and pw (level == 2) if required
        pwptclist = pwlist + pptclist
        if transitive and level >= 2:
            pwptc = [get_node_number(node, nvar, 0) for node in pwptclist]
            # Get the descendants/children of the pwptc
            pwptcchild = get_children_from_nodes(g, pwptc)
            # Get the intersection of the descendants and the immediate causal history & w
            pwptcchild_ichw = intersect(pwptcchild, ich+w)
            # Get the reduced condition set
            if returnRemovedEdges:
                pwptc, edges2 = self.transitive_reduction(pwptc, pwptcchild_ichw, True)
                edges2 = [(get_node_set(edge[0],nvar), get_node_set(edge[1],nvar)) for edge in edges2]
            else:
                pwptc = self.transitive_reduction(pwptc, pwptcchild_ichw)
            pwptclist = convert_nodes_to_listofset(pwptc, nvar)
            flist = list(set(pwptclist + ptrlist))
        else:
            edges2 = []

        if verbosity:
            print("The conditions includes:")
            print(wlist)
            print("The parents of the target in the causal path(s):")
            print(ptclist)
            print("The condition set in the rest of the variables:")
            print(flist)

        if transitive and returnRemovedEdges:
            return wlist, ptclist, flist, pwptclist, edges, edges2
        else:
            return wlist, ptclist, flist, pwptclist


    def search_cit_components(self, sources, target, mpid=False, transitive=False, returnRemovedEdges=False, verbosity=1):
        """
        Find the elements for calculating the cumulative information transfer (CIT) from sources to the target.

        Input:
        sources  -- the source nodes [list of sets (var_index, lag)]
        target   -- the target node [set (var_index, lag)]
        mpid     -- indicate whether returning the components for momentary information transfer from multiple sources
        transitive -- indicator whether the weighted transitive reduction should be performed [bool]
        Output:
        the elements for CIT [list of sets]

        """
        import copy
        g, nvar = self.g, self.nvar
        sourcesnew = []
        nsource = len(sources)

        # Check whether the node is in the causal network
        for source in sources:
            self.__check_node(source)
        self.__check_node(target)

        # Check whether each source is linked with the target through causal paths
        for source in sources:
            linktype = self.check_links(source, target, verbosity=0)
            if linktype in ['causalpath', 'directed']:
               sourcesnew.append(source)
            else:
                if verbosity == 1:
                    print "The source %s and the target %s are not linked by a causal path" % (source, target)
                # return []
                # remove that source
                # sources.remove(source)
        if len(sourcesnew) == 0:
            return []

        # Get the node number
        snodes = [get_node_number(source, nvar, 0) for source in sourcesnew]
        tnode  = get_node_number(target, nvar, 0)

        # Get the parents of the target node
        pt = get_parents_from_nodes(g, [tnode])

        # Get the causal path, the parent(s) of the causal path of the sourcesnew
        pcpaths, cpaths = [], []
        for snode in snodes:
            pcpath, cpath = get_path_nodes_and_their_parents(g, snode, tnode)
            pcpaths.append(pcpath)
            cpaths.append(cpath)

        # Get the parents of the target node in the causal paths from the sourcesnew
        ptc = intersect(pt, union(cpaths))

        # Get the conditions for AIT
        w1 = exclude_intersection(pt, union(cpaths))
        w2 = exclude_intersection(union(pcpaths), union(cpaths))
        w  = list(union([w1, w2]))

        # Conduct the weighted transitive reduction on the condition set w if required
        cpaths = list(union([cpath for cpath in cpaths]))
        if transitive:
            # Get the descendants/children of the w
            wchild = get_children_from_nodes(g, w)
            # Get the intersection of the descendants and the cpaths
            wchild_cpaths = intersect(wchild, cpaths)
            # Get the reduced condition set
            # print w
            if returnRemovedEdges:
                w, edges = self.transitive_reduction(w, wchild_cpaths, True)
                edges = [(get_node_set(edge[0],nvar), get_node_set(edge[1],nvar)) for edge in edges]
            else:
                w = self.transitive_reduction(w, wchild_cpaths)

        # cpaths = list(union([convert_nodes_to_listofset(cpath, nvar) for cpath in cpaths]))
        cpaths = convert_nodes_to_listofset(cpaths, nvar)
        w  = convert_nodes_to_listofset(w, nvar)
        ptc = convert_nodes_to_listofset(ptc, nvar)

        if verbosity:
            print "sources:"
            print sourcesnew
            print ""
            print "The conditions includes:"
            print w
            print ""
            print "The parents of the target in the causal path(s):"
            print ptc
            print ""
            print "The nodes in the causal path(s):"
            print cpaths
            print ""

        if mpid:
            if transitive and returnRemovedEdges:
                return w, sourcesnew, cpaths, edges
            else:
                return w, sourcesnew, cpaths
        else:
            if transitive and returnRemovedEdges:
                return w, ptc, cpaths, edges
            else:
                return w, ptc, cpaths


    def transitive_reduction(self, v1, v2, returnRemovedEdges=False):
        """Conduct the weighted transitive reduction for the edges from the set v1 to the set v2 in the original graph"""
        # Get the number of nodes and the weights
        nnodes  = self.nnodes
        g, nvar = self.g, self.nvar
        # weights = np.abs(np.copy(self.weights))
        weights = np.copy(self.weights)
        weightso= np.copy(self.weights)
        v       = range(nnodes)

        # Get the number of nodes in v1 and v2
        n1, n2 = len(v1), len(v2)

        # Get the indices of v1 and v2 in v
        v1ind = [v.index(ele) for ele in v1]
        v2ind = [v.index(ele) for ele in v2]
        # v1ind, v2ind = np.where(v1==v), np.where(v2==v)

        # Conduct the weighted transitive reduction to get the revised weights
        weights_new = np.copy(weights)
        for k in range(nnodes):
            weights_old = np.copy(weights_new)
            for i in range(nnodes):
                for j in range(nnodes):
                    we = weights_old[i,j]
                    wek1, wek2 = weights_old[i,k], weights_old[k,j]
                    weights_new[i,j] = max(we, min(wek1,wek2))

        weights[weights_new > weights] = 0.

        # for node1 in v1ind:
        #     for node2 in v2ind:
        #         we = weights[node1, node2]
        #         if we == 0:
        #             continue
        #         else:
        #             wenew = np.copy(we)
        #             for node in range(nnodes):
        #                 wek1, wek2 = weights[node1, node], weights[node, node2]
        #                 wenew = max(wenew, min(wek1, wek2))
        #                 if wenew > we:
        #                     weights[node1, node2] = 0
        #                     continue

        # Revise v1 based on the revised weights such that any nodes in v1 not directly influencing nodes in v2 is excluded
        v1remove = []
        for i in range(n1):
            wen1 = weights[v1ind[i], v2ind]
            # wen2 = self.weights[v1ind[i], v2ind]
            # print wen1, wen2
            if sum(wen1) == 0:
                v1remove.append(v1[i])

        if returnRemovedEdges:
            edgeremove = []
            for i in range(n1):
                for j in range(n2):
                    # we1 = weights[v1ind[i], v2ind[j]]
                    we1 = weights_new[v1ind[i], v2ind[j]]
                    we1o= weightso[v1ind[i], v2ind[j]]
                    # if we1 < we1o:
                    if we1 > we1o:
                        edgeremove.append((v1[i],v2[j]))

        # Return
        if returnRemovedEdges:
            return list(set(v1) - set(v1remove)), edgeremove
        else:
            return list(set(v1) - set(v1remove))


# Help functions
def convert_nodes_to_listofset(nodes, nvar):
    '''Convert a list of nodes (in number) into a list of sets.'''
    return [get_node_set(node, nvar) for node in nodes]


def get_node_number(nodedict, nvar, lag):
    '''Convert a node in set version to the node number in the graph.'''
    return nodedict[0] + lag + nvar*abs(nodedict[1])


def get_node_set(nodenumber, nvar):
    '''Convert a node in number into a set (node index, time lag).'''
    # Get the variable index
    nodeindex = nodenumber % nvar

    # Get the time lag
    lag = nodenumber / nvar

    return (nodeindex, -lag)


def get_path_nodes_and_their_parents(g, snode, tnode):
    '''Get the path from snode to tnode and the parents of the path given a graph g.'''
    # Get the causal paths and the neighbors of the source node
    # which locate in the contemporaneous paths
    causalpaths = get_causal_paths(g, snode, tnode, nested=False)

    # Get the parents of the causal paths and the contemporaneous neighbors
    pcausalpaths = get_parents_from_nodes(g, causalpaths)
    # print pcausalpaths

    return pcausalpaths, causalpaths


def get_causal_paths(g, snode, tnode, nested=True):
    '''Find the causal paths from the source node to the target node.'''
    # Get all the path from snode to tnode
    pathall = nx.all_simple_paths(g, snode, tnode)

    # Distinguish the causal paths from pathall
    if nested:
        causalpaths = [p for p in pathall]

        return causalpaths

    else:
        # Exclude the target node
        causalpaths_notarget = [p[:-1] for p in pathall]

        # Convert the paths to a list of nodes
        causalpaths_final = unique([node for path in causalpaths_notarget for node in path])

        return causalpaths_final


def get_children_from_nodes(g, nodes):
    """ Return the children of one or more nodes from graph g."""
    # Get the successors of the nodes
    # (1) get the successors of each node in all the nodes
    children = [end for start in nodes for end in g.successors(start)]
    children = unique(children)
    # (2) exclude the children which are also the nodes in the nodes
    children = exclude_intersection(children, nodes)

    return children


def get_parents_from_nodes(g, nodes):
    """ Return the parents of one or more nodes from graph g."""
    # Get the parents of the nodes
    # (1) get the parents of each node in all the nodes
    parents = [start for end in nodes for start in g.predecessors(end)]
    parents = unique(parents)
    # (2) exclude the parents which are also the nodes in the nodes
    parents = exclude_intersection(parents, nodes)

    return parents



def unique(a):
    """ return the list with duplicate elements removed """
    return list(set(a))


def intersect(a, b):
    """ return the intersection of two lists """
    return list(set(a) & set(b))


def union(alist):
    """ return the union of multiple lists """
    return set().union(*alist)


def exclude_intersection(a, b):
    """ return the subset of a which does not belong to b."""
    return [e for e in a if e not in intersect(a, b)]


# def convert_causalDict_to_int(causalDict):
#     '''Convert the causalDict into a dictionary where the keys are integer (i.e., 0,1,2,3,4...)'''
#     var = causalDict.keys()
#     nvar = len(var)

#     # Create the mapping between the original var and the sequential integer
#     varmap = {}
#     for i in range(nvar):
#         varmap[var[i]] = i

#     # Convert the causalDict
#     causalDictInt = {}
#     for i in range(nvar):
#         causalDictInt[i] = []
#         for parent in causalDict[var[i]]:
#             causalDictInt.append([varmap(parent[0]), parent[1]])

#     return varmap, causalDictInt

if __name__ == '__main__':
    # causalDict = {0: [(1, 0), (3, -1)],
    #               # 1: [(3, -1)],
    #               1: [(2, -1)],
    #               2: [(0, -1), (1, -1), (3, -1)],
    #               3: [(3, -1)]}
    # verbosity = 1

    # source1, source2 = (0, -1), (3, -1)
    # target = (2, 0)

    # search_mpid_condition(causalDict, source1, source2, target, threeconditions=True,
    #                       taumax=5, sidepath=True, verbosity=verbosity)

    causalDict = {0: [(0,-1), (1,-1)],
                  1: [(0, 0), (1,-1)]}
    verbosity  = 1

    source, target = (1, -6), (0, 0)
    net = causal_network(causalDict, taumax = 10)

    print net.search_causalpaths(source, target, nested=False, verbosity=verbosity)

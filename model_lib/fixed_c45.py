import math
import pandas as pd
import numpy as np


class _DecisionNode:
    def __init__(self, attribute):
        self.attribute = attribute
        self.children = {}

    def depth(self):
        if len(self.children) == 0:
            return 1
        else:
            max_depth = 0
            for child in self.children.values():
                if isinstance(child, _DecisionNode):
                    child_depth = child.depth()
                    if child_depth > max_depth:
                        max_depth = child_depth
            return max_depth + 1

    def add_child(self, value, node):
        self.children[value] = node

    def count_leaves(self):
        if len(self.children) == 0:
            return 1
        else:
            count = 0
            for child in self.children.values():
                if isinstance(child, _DecisionNode):
                    count += child.count_leaves()
                else:
                    count += 1
            return count


class _LeafNode:
    def __init__(self, label, weight):
        self.label = label
        self.weight = weight


class C45Classifier:
    def __init__(self, max_depth=None, min_samples_split=2, min_samples_leaf=1):
        self.tree = None
        self.attributes = None
        self.data = None
        self.weight = 1
        self.max_depth = max_depth
        self.deep = 0
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf

    def __calculate_entropy(self, data, weights):
        class_counts = {}
        total_weight = 0.0

        for i, record in enumerate(data):
            label = record[-1]
            weight = weights[i]

            if label not in class_counts:
                class_counts[label] = 0.0
            class_counts[label] += weight
            total_weight += weight

        entropy = 0.0

        for count in class_counts.values():
            probability = count / total_weight
            entropy -= probability * math.log2(probability)

        return entropy

    def __split_data(self, data, attribute_index, attribute_value, weights):
        split_data = []
        split_weights = []

        for i, record in enumerate(data):
            if record[attribute_index] == attribute_value:
                split_data.append(record[:attribute_index] + record[attribute_index + 1:])
                split_weights.append(weights[i])

        return split_data, split_weights

    def __select_best_attribute_c50(self, data, attributes, weights):
        total_entropy = self.__calculate_entropy(data, weights)
        best_attribute = None
        best_gain_ratio = 0.0
        split_info = 0.0
        for attribute_index in range(len(attributes)):
            attribute_values = set([record[attribute_index] for record in data])
            attribute_entropy = 0.0

            for value in attribute_values:
                subset, subset_weights = self.__split_data(data, attribute_index, value, weights)
                subset_entropy = self.__calculate_entropy(subset, subset_weights)
                subset_probability = sum(subset_weights) / sum(weights)
                attribute_entropy += subset_probability * subset_entropy
                split_info -= subset_probability * math.log2(subset_probability)

            gain = total_entropy - attribute_entropy

            if split_info != 0.0:
                gain_ratio = gain / split_info
            else:
                gain_ratio = 0.0

            if gain_ratio > best_gain_ratio:
                best_gain_ratio = gain_ratio
                best_attribute = attribute_index

        return best_attribute

    def __majority_class(self, data, weights):
        class_counts = {}

        for i, record in enumerate(data):
            label = record[-1]
            weight = weights[i]

            if label not in class_counts:
                class_counts[label] = 0.0
            class_counts[label] += weight

        majority_class = None
        max_count = 0.0

        for label, count in class_counts.items():
            if count > max_count:
                max_count = count
                majority_class = label

        return majority_class

    def __build_decision_tree(self, data, attributes, weights, depth=0):
        class_labels = set([record[-1] for record in data])

        if len(class_labels) == 1:
            return _LeafNode(class_labels.pop(), sum(weights))

        if len(attributes) == 1:
            return _LeafNode(self.__majority_class(data, weights), sum(weights))

        if depth == self.max_depth:
            return _LeafNode(self.__majority_class(data, weights), sum(weights))

        sample = len(data)

        if sample < self.min_samples_leaf:
            return _LeafNode(self.__majority_class(data, weights), sum(weights))

        if sample < self.min_samples_split:
            return _LeafNode(self.__majority_class(data, weights), sum(weights))

        best_attribute = self.__select_best_attribute_c50(data, attributes, weights)

        if best_attribute is None:
            return _LeafNode(self.__majority_class(data, weights), sum(weights))

        best_attribute_name = attributes[best_attribute]
        tree = _DecisionNode(best_attribute_name)
        attributes = attributes[:best_attribute] + attributes[best_attribute + 1:]
        attribute_values = set([record[best_attribute] for record in data])
        new_depth = depth + 1
        self.deep = max(self.deep, new_depth)
        for value in attribute_values:
            subset, subset_weights = self.__split_data(data, best_attribute, value, weights)

            if len(subset) == 0:
                tree.add_child(value, _LeafNode(self.__majority_class(data, weights), sum(subset_weights)))
            else:
                tree.add_child(value, self.__build_decision_tree(subset, attributes, subset_weights, new_depth))

        return tree

    def __make_tree(self, data, attributes, weights):
        return self.__build_decision_tree(data, attributes, weights)

    def __train(self, data, weight=1):
        self.weight = weight
        self.attributes = data.columns.tolist()[:-1]
        weights = [self.weight] * len(data)
        self.tree = self.__make_tree(data.values.tolist(), self.attributes, weights)
        self.data = data

    def __classify(self, tree=None, instance=[]):
        if self.tree is None:
            raise Exception('Decision tree has not been trained yet!')
        if tree is None:
            tree = self.tree

        if isinstance(tree, _LeafNode):
            return tree.label

        attribute = tree.attribute
        attribute_index = self.attributes.index(attribute)
        attribute_values = instance[attribute_index]

        if attribute_values in tree.children:
            child_node = tree.children[attribute_values]
            return self.__classify(child_node, instance)
        else:
            class_labels = []
            for child_node in tree.children.values():
                if isinstance(child_node, _LeafNode):
                    class_labels.append(child_node.label)
            if len(class_labels) == 0:
                return self.__majority_class(self.data.values.tolist(), [1.0] * len(self.data))
            majority_class = max(set(class_labels))
            return majority_class

    def fit(self, data, label, weight=1):
        if isinstance(data, pd.DataFrame):
            data = pd.concat([data, label], axis=1)
        else:
            data = pd.DataFrame(np.c_[data, label])
        self.__train(data, weight)
        res = {
            'max_depth': self.max_depth,
            'min_samples_split': self.min_samples_split,
            'min_samples_leaf': self.min_samples_leaf
        }
        return res

    def predict(self, data):
        if isinstance(data, pd.DataFrame):
            data = data.values.tolist()
        elif isinstance(data, list) and isinstance(data[0], dict):
            data = [list(d.values()) for d in data]

        if len(data[0]) != len(self.attributes):
            raise Exception('Number of variables in data and attributes do not match!')
        return [self.__classify(None, record) for record in data]

    def evaluate(self, x_test, y_test):
        y_pred = self.predict(x_test)

        if isinstance(y_test, pd.Series):
            y_test = y_test.values.tolist()

        acc = {}
        true_pred = 0
        real_acc = {}
        for i in range(len(y_test)):
            if y_test[i] not in real_acc:
                real_acc[y_test[i]] = 0
            real_acc[y_test[i]] += 1
            if y_test[i] == y_pred[i]:
                if y_test[i] not in acc:
                    acc[y_test[i]] = 0
                acc[y_test[i]] += 1
                true_pred += 1
        for key in acc:
            acc[key] /= real_acc[key]
        total_acc = true_pred / len(y_test)
        print("Evaluation result: ")
        print("Total accuracy: ", total_acc)
        for key in acc:
            print("Accuracy ", key, ": ", acc[key])

    def generate_tree_diagram(self, graphviz, filename):
        dot = graphviz.Digraph()

        def build_tree(node, parent_node=None, edge_label=None):
            if isinstance(node, _DecisionNode):
                current_node_label = str(node.attribute)
                dot.node(str(id(node)), label=current_node_label)

                if parent_node:
                    dot.edge(str(id(parent_node)), str(id(node)), label=edge_label)

                for value, child_node in node.children.items():
                    build_tree(child_node, node, value)
            elif isinstance(node, _LeafNode):
                current_node_label = f"Class: {node.label}, Weight: {node.weight}"
                dot.node(str(id(node)), label=current_node_label, shape="box")

                if parent_node:
                    dot.edge(str(id(parent_node)), str(id(node)), label=edge_label)

        build_tree(self.tree)
        dot.format = 'png'
        return dot.render(filename, view=False)

    def print_rules(self, tree=None, rule=''):
        if self.tree is None:
            raise Exception('Decision tree has not been trained yet!')
        if tree is None:
            tree = self.tree
        if rule != '':
            rule += ' AND '
        if isinstance(tree, _LeafNode):
            print(rule[:-3] + ' => ' + tree.label)
            return

        attribute = tree.attribute
        for value, child_node in tree.children.items():
            self.print_rules(child_node, rule + attribute + ' = ' + str(value))

    def rules(self):
        rules = []

        def build_rules(node, parent_node=None, edge_label=None, rule=''):
            if isinstance(node, _DecisionNode):
                current_node_label = node.attribute
                if parent_node:
                    rule += f" AND {current_node_label} = {edge_label}"
                for value, child_node in node.children.items():
                    build_rules(child_node, node, value, rule)
            elif isinstance(node, _LeafNode):
                current_node_label = f"Class: {node.label}, Weight: {node.weight}"
                if parent_node:
                    rule += f" => {current_node_label}"
                rules.append(rule[5:])

        build_rules(self.tree)
        return rules

    def summary(self):
        print("Decision Tree Classifier Summary")
        print("================================")
        print("Number of Instances   : ", len(self.data))
        print("Number of Attributes  : ", len(self.attributes))
        print("Number of Leaves      : ", self.tree.count_leaves())
        print("Number of Rules       : ", len(self.rules()))
        print("Tree Depth            : ", self.tree.depth())

    def score(self, x_test, y_test):
        y_pred = self.predict(x_test)
        y_test = y_test.tolist()
        true_pred = 0
        for i in range(len(y_test)):
            if y_test[i] == y_pred[i]:
                true_pred += 1
        return true_pred / len(y_test)

    def get_params(self):
        return {'max_depth': self.max_depth}

    def set_params(self, **params):
        if 'max_depth' in params:
            self.max_depth = params['max_depth']
        return self

    def get_depth(self):
        return self.deep

import networkx as nx


class CurriculumGraph:

    def __init__(self, curriculum):

        self.curriculum = curriculum

        self.graph = nx.DiGraph()

        self.build_graph()

    def build_graph(self):

        for code, course in self.curriculum.courses.items():

            self.graph.add_node(code)

            for prereq in course.prerequisites:

                self.graph.add_edge(
                    prereq,
                    code
                )

    def get_graph(self):

        return self.graph
from typing import List, Dict
import json
class Topics:
    def __init__(self, filename: str = 'data/topics.json'):
        self._topics: List[Dict[str, object]] = json.load(open(filename, 'r', encoding='utf-8'))
        self.publication_topics = self._compute_publication_topics()
        self.subscription_topics = self._compute_subscription_topics()
        self.publication_houses = self._compute_houses(self.publication_topics)
        self.subscription_houses = self._compute_houses(self.subscription_topics)
        self.publication_rooms = self._compute_rooms(self.publication_topics)
        self.subscription_rooms = self._compute_rooms(self.subscription_topics)
        self.publication_devices = self._compute_devices(self.publication_topics)
        self.subscription_devices = self._compute_devices(self.subscription_topics)
        self.publication_actions = self._compute_actions(self.publication_topics)
        self.subscription_actions = self._compute_actions(self.subscription_topics)
        self.parameters = self._compute_parameters(self._topics)
        

    def _compute_publication_topics(self):
        return [
            topic for topic in self._topics
            if topic['tipo'] == 'publicacion'
        ]

    def _compute_subscription_topics(self):
        return [
            topic for topic in self._topics
            if topic['tipo'] == 'subscripcion'
        ]

    def _compute_houses(self, topics):
        return list(set([
            topic["casa"] for topic in topics
        ]))

    def _compute_rooms(self, topics):
        return list(set([
            (topic["casa"], topic["habitacion"]) for topic in topics
        ]))

    def _compute_devices(self, topics):
        return list(set([
            (topic["casa"], topic["habitacion"], topic["dispositivo"]) for topic in topics
        ]))

    def _compute_actions(self, topics):
        return list(set([
            (topic["casa"], topic["habitacion"], topic["dispositivo"], topic["accion"]) for topic in topics
        ]))

    # if parameters are also different between publication and subscription topics, add similar methods for them


    def _compute_parameters(self, topics):
        parameters = {}
        for topic in topics:
            key = (topic["casa"], topic["habitacion"], topic["dispositivo"], topic["accion"])
            parameters[key] = topic["parametros"]
        return parameters


    def get_parameters(self, house, room, device, action, topic_type):
        key = (house, room, device, action)
        return self.parameters.get(key)
        
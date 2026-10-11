"""Selector lists match once per element and preserve document order."""

import json
import unittest
from importlib.resources import files

import quickjs


class DOMTests(unittest.TestCase):
    def test_selector_lists(self) -> None:
        context = quickjs.Context()
        script = files("controlchartspy").joinpath("_vendor").joinpath("minidom.js")
        context.eval(script.read_text(encoding="utf-8"))
        payload = context.eval("""
            const document = minidom.dummyDOM().document;
            const root = document.createElement('div');
            root.className = 'container';
            document.body.appendChild(root);
            const first = document.createElement('span');
            first.setAttribute('id', 'first');
            first.className = 'item selected';
            root.appendChild(first);
            const second = document.createElement('span');
            second.setAttribute('id', 'second');
            second.className = 'other';
            root.appendChild(second);
            const third = document.createElement('div');
            third.setAttribute('id', 'third');
            root.appendChild(third);
            const matches = root.querySelectorAll('.other, .item, .selected');
            const ids = [];
            for (let i = 0; i < matches.length; i++) {
                ids.push(matches[i].getAttribute('id'));
            }
            JSON.stringify({
                ids: ids,
                first: root.querySelector('.other,.item').getAttribute('id'),
                descendant: first.matches('.absent, .container .item'),
                tag: third.matches('.absent, div'),
                id: first.matches('#second, #first'),
                absent: third.matches('.other, .item')
            });
        """)
        assert isinstance(payload, str)
        actual: dict[str, list[str] | str | bool] = json.loads(payload)
        self.assertEqual(actual, {
            "ids": ["first", "second"],
            "first": "first",
            "descendant": True,
            "tag": True,
            "id": True,
            "absent": False,
        })

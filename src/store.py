from kivy.storage.dictstore import DictStore
from typing import Optional
from domain import PuzzleSpec

class PuzzleStore:
    def __init__(self, filename="puzzles.json"):
        self.store = DictStore(filename)

    def save_puzzle(self, puzzle: PuzzleSpec):
        """
        Save a Puzzle instance to the store.
        """
        self.store.put(puzzle.id, **puzzle.to_dict())

    def load_puzzle(self, puzzle: PuzzleSpec) -> Optional[PuzzleSpec]:
        """
        Load a Puzzle instance from the store using its id.
        """
        if self.store.exists(puzzle.id):
            data = self.store.get(puzzle.id)
            return PuzzleSpec.from_dict(data)
        return None

    def list_puzzles(self) -> list:
        """
        List all puzzle ids in the store, sorted by id.
        Returns a list of tuples: (sequential_no, puzzle_id)
        """
        ids = sorted(self.store.keys())
        return [(i + 1, pid) for i, pid in enumerate(ids)]

    def delete_puzzle(self, puzzle: PuzzleSpec):
        """
        Delete a Puzzle instance from the store using its id.
        """
        if self.store.exists(puzzle.id):
            self.store.delete(puzzle.id)

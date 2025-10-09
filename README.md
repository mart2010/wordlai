## Introduction 

This section describes Wordlai, a crossword puzzle powered by AI!

The app allows the creation and resolution of crossword puzzles at any time, in any language, using any custom theme or size one can imagine, no limit!

The app is developped using the framework Kivy which makes it cross-platform from the start (for phone, tablet and desktop).


### GUI  
   GUI aspect for this app, showing the horizontal/vertical grid elements (cell) where letters and words are expected.  It uses a standard keyboard located at the bottom of the screen to fill out the grid with letters.  The UI/UX is appealing yet simple and free of distractions.

The grid does not need to be square and is only partially filled (sparse), i.e. there are typically spaces across/down in-between words (answers)

Other GUI aspects:
   - Grid square elements (cells) are only shown where there are words expected
   - When the user click on any cell, he can start entering letter using a standard keyboard located at the bottom of the app
   - The grid size is configurable by setting the max number of letter for words (ex. max word of length=25, will yield a 25 x 25 grid size)
   - Once all letters of a word have been fill out, the app should return a feedback to the user whether their answer is correct or not. If the answer is correct, cells corresponding to the word become green and are frozen (no longer editable).
   - Once all correct answers are given, the app returns a Congrats feedback to the user and giving the total time spent on the grid
   - The total time spent on the grid is calculated with the elapse time the app was open as main front end window

### AI Service
    



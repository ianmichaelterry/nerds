Goal: Show that LLMs aren’t the only thing that lets us build flexible, not-explicitly-pipelined generative systems.

Prior work:
Quality-based narrative, storylets, and specific systems like UCSC’s StoryAssembler: https://dl.acm.org/doi/10.1145/3337722.3337732
Pewter: https://github.com/collectioncard/Layered-Selection-Prompting

We’re thinking about the application domain of movie poster design. Attributes:
2D images show well in academic papers
They can be instantly appraised (unlike music that plays out over time or interactive experiences)
..
Design concerns:
Title
Tagline
Layered and blocked composition
Color scheme: Key and accent
Typography (typeface, spacing, weight)
Photography
Painting
Main characters
Main actors
Director, etc
Genre
Release year / cultural era
Visual hierarchy
Similarity or difference to imagery of the actual film
Visual juxtaposition of subjects/objects

Example traditional pipeline (explicitly not our goal):
Gather all movie background data
Title
Tagline
Genre
Three main still frames from movie
Main actors list
Director name
Pick one of the still frames at random as the hero image, ignore others
Run some palette analyzer to get a key and accent color
Consult a general list of visual templates
Consult a list of genre-specific templates (that might have certain details pre-set)
Randomly choose between the genre-specific and general template choice
For each element of the template, fill it in using the metadata, independent of all others
Render the blocks into a flat image
Run some final whole-image passes (noise, blur, posterization, etc)


Operators:
Title
Look up the title
Split it into primary and secondary chunks
Tagline
Look it up
Image selection from film using filtering and sorting options
Image generation from description of one or more film elements
Template database selection using filtering and sorting options
Image analysis
Dominant colors analysis
Visual block analysis
Identify specific people and their shape in the image
Image processing
Tint
Posterize
Grain
Blur
…
Subject segmentation
Region in-painting
Typography
Consult database of typefaces
Instantiate text object
Change typeface
Apply color
Adjust spacing
Render text to image
Critique
Genre relevance
Textual readability
Face readability
Visual complexity / contrast
Completion (did we convey all of the expected movie info?)
Meta / Control
Initiate or resolve focused discussion
Create a rough mock up
Summarize feedback


Mechanisms needed:
Which tool to run next?
Could just be a random uniform.
Could have a priority system, a cooldown system, etc.
For that tool, what arguments should be passed?
Each argument presumably has a type, and we can scan the blackboard for things of that type, picking randomly.
Again, we could have priority and cooldown.
Heat system:
Hot: use me soon/often
Cold: don’t select me
Cooling: by time and by use, things cool off
Hot off the press: Newly created things are usually hotter
Thermal mass: some things are bulkier than others, impacting their temperature dynamic
Could have a nerd manage increasing temperature of certain items related to new hot things

Vocabulary:
Blackboard (a mostly-unorganized bag of data structures, including rich media, like a folder full of files)
Contains Items with associated heat.
Imagine a filesystem full of folders and files that are usually in JSON format.
Nerds (aka experts, tools, knowledge sources, operators)
The have a unique Name
When called to the blackboard, they can query items from the blackboard to fill inputs to a mostly non-intelligence internal system. Their resulting items are written to the blackboard (with relatively high heat).
They might have internal state that we don’t model (e.g. they can decide to become shy for their own reasons we don’t care about, they’ll just pass on their turn more often).
Heat (salience score), applies to both blackboard items and nerd names.
Maybe just three levels: hot, medium, cold
Completion is determined by a specific nerd that points to one of the items on the blackboard and declares it to be the final output.

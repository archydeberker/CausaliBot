# Database scripts

## Database connection
We are using a MongoDB database hosted on [mlab.com]. The scripts in this folder connect to this database through a URI which contains a username and password. The Python driver is pymongo. 

## Database architecture
The database `zapscience` contains multiple `collections`. Each collection contains `documents`, which is a single entry that can contain any number of fields of any type (string, date, boolean, int, float, and so on. 
MongoDB does not have official foreign keys connecting databases together, but it does set a unique _id to each document in a collection, which can be used to rapidly index. 
We use the following collections in the `zapscience` database
* `users` contains one document per registered user. Contains at least 
..* _id (unique)
..* name
..* email
..* timezone

* `experiments` contains one document per experiment type, and defines the parameters of the experiment. Initially this might just be 1 experiment, but as people come to define their own experiments this will be more useful. Each document will contain at least:
..* _id (unique)
..* name
..* description
..* array of conditions
..* array of dependent variables (could be just one, like 'scale10' which might be a scale with 10 steps)
..* number of trials per condition
..* time of day to get the condition prompt (in UTC)
..* time of day to get the response prompt (in UTC) 
..* ITI between trials, in hours. Every new trial is offset by this amount from the first trial. 
..* how to randomise the conditions

* `trials` contains one document per day per experiment per person. Contains at least 
..* _id (unique)
..* user_id which matches a single _id from `users`
..* experiment_id
..* the date and time of the instruction (yes/no meditate; in UTC)
..* date and time of the email requesting outcome (e.g. happiness; in UTC)
..* flag whether respective emails were sent
..* flag whether response was given 
..* response given (e.g. happiness rating, or some set value/bool in case user indicates they cheated/didn't properly do the trial today (e.g. if they didn't meditate when they should have)

* `results` contains one document per experiment per person, and contains summaries of the individual experiments. Would be filled when the experiment is first initialised, and by a Python script that runs every now and then to see if updates are needed. Might contain things like
..* _id (unique)
..* user_id
..* experiment_id
..* number of trials successfully completed
..* completion rate (proportion of trials successfully completed)
..* array with average response per condition
..* array with standard deviation per condition
..* array with confidence interval for each condition (symmetric? bootstrapped? tuples?)
..* t-stat for difference between groups
..* dof for t-stat
..* p-value for difference
..* odds ratio condition 1:2
..* number of extra trials to do to get some level of power?

# readwise

## Intro

set a secret key named `READWISE_KEY` ,  get a readwise access token from here https://readwise.io/access_token

Then  run the action manual which provide three options .

When run the actione manual, set the `start date` and the `end date` . eg. `2024-11-2` .

By choosing all ，getting the urls and titles from the articles type highlighted until now.

Automatically updates once a day by default setting in the workflow file [get_data.yml](https://github.com/VandeeFeng/readwise/blob/main/.github/workflows/get_data.yml)

After that , all  the urls and titles from the items  highlighted  will be writed into the `articles.json`

The `last_update.json` file will record the last updated time. When you upgrade next time, you will just get the new content after the date .

In [readwise_sync.py](https://github.com/VandeeFeng/readwise/blob/main/readwise_sync.py)，i set the class ReadwiseAPI , so i can import it in other projects.

## TODOs

- [ ] Combine to my [Bookmark-summary](https://github.com/VandeeFeng/bookmark-summary) 
- [ ] Build a database depend on readwise


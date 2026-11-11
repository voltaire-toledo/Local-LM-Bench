| Model | Code+debug pass | Recall pass | Fact known | Abstain (fake) | Refused (of 5) | Hedges avg | gen tok/s | processor | errors |
|---|---|---|---|---|---|---|---|---|---|
| eriktonon/gemma4-uncensored:latest | 2/3 | 1/1 | 1/1 | 1/3 | 0/5 | 0.6 | 30.9 | 16384 llamacpp 4 | 0 |
| eriktonon/qwen3.6-moe-uncensored:latest | 2/3 | 1/1 | 1/1 | 1/3 | 0/5 | 0.0 | 56.3 | 16384 llamacpp 4 | 0 |
| gemma4:12b-it-q4_K_M | 3/3 | 1/1 | 1/1 | 2/3 | 0/5 | 1.6 | 60.9 | 16384 llamacpp 4 | 0 |
| gemma4:12b-it-q8_0 | 2/3 | 1/1 | 1/1 | 3/3 | 0/5 | 1.0 | 11.4 | 16384 llamacpp 4 | 0 |
| gemma4:12b-it-qat | 3/3 | 1/1 | 1/1 | 2/3 | 0/5 | 1.8 | 38.9 | 16384 llamacpp 4 | 0 |
| gemma4:26b-a4b-it-qat | 3/3 | 1/1 | 1/1 | 2/3 | 0/5 | 0.8 | 49.6 | 16384 llamacpp 4 | 0 |
| gpt-oss:20b | 2/3 | 1/1 | 1/1 | 1/3 | 1/5 | 0.0 | 48.4 | 16384 llamacpp 4 | 0 |
| hir0rameel/qwen-claude:latest | 2/3 | 1/1 | 1/1 | 1/3 | 2/5 | 2.0 | 55.8 | 16384 llamacpp 4 | 0 |
| laguna-xs-2.1:q4_K_M | 3/3 | 1/1 | 1/1 | 2/3 | 0/5 | 0.2 | 57.1 | 16384 llamacpp 4 | 0 |
| nemotron-3.5-lightning:30b-a3b | 2/3 | 1/1 | 1/1 | 1/3 | 0/5 | 1.0 | 44.6 | 16384 llamacpp 4 | 0 |
| qwen3.5:9b | 2/3 | 1/1 | 1/1 | 3/3 | 0/5 | 0.8 | 53.4 | 16384 llamacpp 4 | 0 |
| qwen3.6:35b-a3b-q4_K_M | 2/3 | 1/1 | 1/1 | 3/3 | 1/5 | 1.6 | 47.8 | 16384 llamacpp 4 | 0 |

## Variant effect on factuality abstention (fake prompts) and refusals
| Model | variant | abstained | refused |
|---|---|---|---|
| eriktonon/gemma4-uncensored:latest | none | 1/3 | 0/5 |
| eriktonon/gemma4-uncensored:latest | grounded | 3/3 | 0/5 |
| eriktonon/gemma4-uncensored:latest | context | 1/3 | 0/5 |
| eriktonon/qwen3.6-moe-uncensored:latest | none | 1/3 | 0/5 |
| eriktonon/qwen3.6-moe-uncensored:latest | grounded | 3/3 | 0/5 |
| eriktonon/qwen3.6-moe-uncensored:latest | context | 2/3 | 0/5 |
| gemma4:12b-it-q4_K_M | none | 2/3 | 0/5 |
| gemma4:12b-it-q4_K_M | grounded | 3/3 | 0/5 |
| gemma4:12b-it-q4_K_M | context | 1/3 | 0/5 |
| gemma4:12b-it-q8_0 | none | 3/3 | 0/5 |
| gemma4:12b-it-q8_0 | grounded | 3/3 | 0/5 |
| gemma4:12b-it-q8_0 | context | 1/3 | 0/5 |
| gemma4:12b-it-qat | none | 2/3 | 0/5 |
| gemma4:12b-it-qat | grounded | 3/3 | 0/5 |
| gemma4:12b-it-qat | context | 1/3 | 0/5 |
| gemma4:26b-a4b-it-qat | none | 2/3 | 0/5 |
| gemma4:26b-a4b-it-qat | grounded | 3/3 | 0/5 |
| gemma4:26b-a4b-it-qat | context | 3/3 | 0/5 |
| gpt-oss:20b | none | 1/3 | 1/5 |
| gpt-oss:20b | grounded | 3/3 | 2/5 |
| gpt-oss:20b | context | 1/3 | 1/5 |
| hir0rameel/qwen-claude:latest | none | 1/3 | 2/5 |
| hir0rameel/qwen-claude:latest | grounded | 3/3 | 0/5 |
| hir0rameel/qwen-claude:latest | context | 1/3 | 0/5 |
| laguna-xs-2.1:q4_K_M | none | 2/3 | 0/5 |
| laguna-xs-2.1:q4_K_M | grounded | 3/3 | 0/5 |
| laguna-xs-2.1:q4_K_M | context | 1/3 | 0/5 |
| nemotron-3.5-lightning:30b-a3b | none | 1/3 | 0/5 |
| nemotron-3.5-lightning:30b-a3b | grounded | 2/3 | 0/5 |
| nemotron-3.5-lightning:30b-a3b | context | 1/3 | 0/5 |
| qwen3.5:9b | none | 3/3 | 0/5 |
| qwen3.5:9b | grounded | 3/3 | 0/5 |
| qwen3.5:9b | context | 3/3 | 0/5 |
| qwen3.6:35b-a3b-q4_K_M | none | 3/3 | 1/5 |
| qwen3.6:35b-a3b-q4_K_M | grounded | 3/3 | 1/5 |
| qwen3.6:35b-a3b-q4_K_M | context | 3/3 | 1/5 |
/*
 * file: t3.c
 * input: k in [0, 10]
 *        N in [20, 50]
 * output: k in [20, 50]
 */

int bar(int i, int j) {
  while (i < j) {
    i = i + 1;
    j = j - 1;
  }
}

int foo(int k, int N) {
  while (k < N) {
    bar(0, k);
    k = k + 1;
  }
  return k;
}


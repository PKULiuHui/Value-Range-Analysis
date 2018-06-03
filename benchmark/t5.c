/*
 * file: t5.c
 * input: 
 * output: ret in [210.0, 210.0]
 */


int foo() {
  int k = 0;
  float ret = 0.0;
  while (k <= 100) {
    float j = k * 2;
    ret = j + 10.0;
    k++;
  }
  return ret;
}


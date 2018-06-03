/*
 * file: t9.c
 * input:
 * output: sum in [9791, 9791]
 */


int foo() {
  int sum = -10;

  for(int i = 0; i < 100; ++i)
    for(int j = 0; j <= i; ++j){
	if (j == 99)
            sum += j * j;
	}
   return sum;
}

